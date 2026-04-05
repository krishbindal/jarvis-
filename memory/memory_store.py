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
            timeout=5
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

def _fetch_embedding_in_bg(role: str, content: str, context: Dict):
    """Fetch embedding and store asynchronously."""
    vec = get_embedding(content)
    blob = struct.pack(f'{len(vec)}f', *vec) if vec else None
    with _LOCK:
        _DB.add_interaction(role, content, context=context, embedding=blob)

def save_interaction(user_input: str, steps: List[Dict[str, Any]], result: Dict[str, Any]) -> None:
    """Save interaction with content and metadata (computes vectors in background)."""
    threading.Thread(target=_fetch_embedding_in_bg, args=("user", user_input, {"steps": steps}), daemon=True).start()
    threading.Thread(target=_fetch_embedding_in_bg, args=("assistant", str(result.get("output", "")), {"original_query": user_input}), daemon=True).start()

def get_recent_history(limit: int = 5) -> List[Dict[str, Any]]:
    """Fetch recent history from SQLite as list of dicts."""
    with _LOCK:
        rows = _DB.get_recent_history(limit)
    # Build into the format ai_engine._format_history expects
    result = []
    for row in rows:
        result.append({
            "user_input": row.get("content", "") if row.get("role") == "user" else "",
            "steps": [],
            "result": {"output": row.get("content", "") if row.get("role") == "assistant" else ""},
        })
    return result

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
    query_norm = np.linalg.norm(query_vec)

    for entry in all_embeddings:
        blob = entry["embedding"]
        content = entry["content"]
        role = entry["role"]
        if not blob:
            continue
        try:
            vec_tuple = struct.unpack(f'{len(blob)//4}f', blob)
            past_vec = np.array(vec_tuple)
            score = np.dot(query_vec, past_vec) / (query_norm * np.linalg.norm(past_vec))

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
    # Simple direct query
    import sqlite3
    db_path = "memory/jarvis.db"
    try:
        with sqlite3.connect(db_path) as conn:
            c = conn.cursor()
            c.execute("SELECT value FROM knowledge WHERE key = ?", (key,))
            res = c.fetchone()
            return res[0] if res else None
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
