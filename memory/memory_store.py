import threading
import struct
from typing import Any, Dict, List, Optional

import requests

try:
    import numpy as np  # type: ignore
except Exception:  # noqa: BLE001
    np = None

from .database import MemoryDB

OLLAMA_BASE = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"
_LOCK = threading.Lock()
_DB = MemoryDB()

def get_embedding(text: str) -> Optional[List[float]]:
    """Fetch embedding from local Ollama instance."""
    try:
        response = requests.post(
            f"{OLLAMA_BASE}/api/embeddings",
            json={"model": EMBED_MODEL, "prompt": text},
            timeout=1.0
        )
        return response.json().get("embedding")
    except Exception:
        return None

def cosine_similarity(v1, v2):
    """Simple cosine similarity for vector comparison."""
    if not v1 or not v2 or not np:
        return 0
    v1, v2 = np.array(v1), np.array(v2)
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

# Never create an unlimited number of background requests or threads.
_MAX_EMBEDDING_WORKERS = 8
_EMBEDDING_SLOTS = threading.BoundedSemaphore(_MAX_EMBEDDING_WORKERS)


def _fetch_embedding_in_bg(interaction_id: int, content: str) -> None:
    """Update an already persisted row; never duplicate or lose the transcript."""
    try:
        vec = get_embedding(content)
        if not vec or len(vec) > 8192:
            return
        blob = struct.pack(f"{len(vec)}f", *vec)
        with _LOCK:
            _DB.update_interaction_embedding(interaction_id, blob)
    except (OSError, ValueError, TypeError, struct.error):
        # A failed local embedding must not destroy the saved text.
        pass
    finally:
        _EMBEDDING_SLOTS.release()


def save_interaction(user_input: str, steps: List[Dict[str, Any]], result: Dict[str, Any]) -> None:
    """Persist user/assistant text in order before requesting optional embeddings.

    SQLite inserts are bounded and synchronous; embeddings are best-effort.
    If all worker slots are busy, retain text without an embedding.
    """
    user_text = str(user_input or "").strip()
    result = result if isinstance(result, dict) else {}
    assistant_text = str(result.get("output") or result.get("message") or "").strip()
    rows = []
    with _LOCK:
        if user_text:
            rows.append((_DB.add_interaction("user", user_text, {"steps": steps}), user_text))
        if assistant_text:
            rows.append((_DB.add_interaction("assistant", assistant_text, {"original_query": user_text}), assistant_text))

    for interaction_id, content in rows:
        if not _EMBEDDING_SLOTS.acquire(blocking=False):
            continue  # Message is stored; only optional vector generation is skipped.
        try:
            worker = threading.Thread(
                target=_fetch_embedding_in_bg,
                args=(interaction_id, content),
                name="memory-embedding",
                daemon=True,
            )
            worker.start()
        except (OSError, RuntimeError):
            _EMBEDDING_SLOTS.release()


def get_recent_history(limit: int = 5) -> List[Dict[str, Any]]:
    """Return actual conversation turns rather than unrelated user/assistant rows."""
    try:
        safe_limit = max(1, min(int(limit), 100))
    except (ValueError, TypeError):
        safe_limit = 5

    with _LOCK:
        rows = _DB.get_recent_history(safe_limit * 2 + 2)

    turns: List[Dict[str, Any]] = []
    for row in rows:
        role = row.get("role")
        content = str(row.get("content") or "")
        if role == "user":
            turns.append({"user_input": content, "steps": [], "result": {}})
        elif role == "assistant":
            if turns and not turns[-1]["result"]:
                turns[-1]["result"] = {"output": content}
            else:
                turns.append({"user_input": "", "steps": [], "result": {"output": content}})
    return turns[-safe_limit:]


def get_relevant_context(user_input: str, limit: int = 3) -> List[Dict[str, Any]]:
    """Semantic context retrieval using embeddings (bulk Numpy search)."""
    if not np:
        return get_recent_history(limit)

    query_vec = get_embedding(user_input)
    if not query_vec:
        return get_recent_history(limit)

    query_vec = np.array(query_vec)

    with _LOCK:
        all_embeddings = _DB.get_all_embeddings()

    if not all_embeddings:
        return get_recent_history(limit)

    scored = []
    query_norm = float(np.linalg.norm(query_vec))
    if not np.isfinite(query_norm) or query_norm <= 0:
        return get_recent_history(limit)

    for entry in all_embeddings:
        blob = entry["embedding"]
        content = entry["content"]
        role = entry["role"]
        if not blob:
            continue
        try:
            vec_tuple = struct.unpack(f'{len(blob)//4}f', blob)
            past_vec = np.array(vec_tuple)
            if len(past_vec) != len(query_vec):
                continue
            past_norm = float(np.linalg.norm(past_vec))
            if not np.isfinite(past_norm) or past_norm <= 0:
                continue
            score = float(np.dot(query_vec, past_vec)) / (query_norm * past_norm)
            if not np.isfinite(score):
                continue

            # Boost score for actual knowledge sources
            if role == "knowledge_source":
                score *= 1.1

            scored.append((score, {
                "user_input": content if role in ["user", "knowledge_source"] else "",
                "steps": [],
                "result": {"output": content if role == "assistant" else ""},
                "source": entry.get("context", {}).get("filename", "Memory") if role == "knowledge_source" else "History"
            }))
        except Exception:
            pass

    scored.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in scored[:limit]]


def store_preference(key: str, value: Any) -> None:
    """Store learned preference in SQLite."""
    with _LOCK:
        _DB.upsert_knowledge(key, str(value), category="preference")

def get_preference(key: str) -> Optional[str]:
    """Retrieve learned preference."""
    try:
        with _LOCK:
            return _DB.get_preference(key)
    except Exception:
        return None

# ─── Background Observer Helpers ───────────────────────────

def log_observation(kind: str, target: str, meta: Dict | None = None) -> None:
    """Persist lightweight observation."""
    with _LOCK:
        _DB.log_observation(kind, target, meta)


def record_pattern(sequence: List[str], label: str | None = None) -> dict:
    """Store a pattern with optional embedding to enable semantic grouping."""
    vec = get_embedding(" -> ".join(sequence)) or []
    blob = struct.pack(f'{len(vec)}f', *vec) if vec else None
    with _LOCK:
        return _DB.record_pattern(sequence, label, blob)


def mark_pattern_suggested(sequence: List[str]) -> None:
    with _LOCK:
        _DB.mark_pattern_suggested(sequence)


def top_patterns(min_count: int = 2, limit: int = 5) -> List[dict]:
    with _LOCK:
        return _DB.get_top_patterns(min_count=min_count, limit=limit)


def add_scheduled_task(label: str, command: str, run_at, recur_seconds: int = 0, auto_execute: bool = False,
                       source: str = "user", metadata: Dict | None = None) -> int:
    with _LOCK:
        return _DB.add_scheduled_task(label, command, run_at, recur_seconds, auto_execute, source, metadata)


def due_tasks(now=None) -> List[dict]:
    with _LOCK:
        return _DB.due_tasks(now=now)


def mark_task_run(task_id: int, status: str = "completed") -> None:
    with _LOCK:
        _DB.mark_task_run(task_id, status)
