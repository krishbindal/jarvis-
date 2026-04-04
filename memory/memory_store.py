import threading
import numpy as np
import requests
from typing import Any, Dict, List, Optional
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
    if not v1 or not v2: return 0
    v1, v2 = np.array(v1), np.array(v2)
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

def save_interaction(user_input: str, steps: List[Dict[str, Any]], result: Dict[str, Any]) -> None:
    """Save interaction with content and metadata."""
    content = f"User: {user_input}\nResult: {result.get('output', 'Success')}"
    # In background (or simple thread) optionally generate/update embeddings if needed
    # For now, we store the raw content in SQLite for fast retrieval
    with _LOCK:
        _DB.add_interaction("user", user_input, context={"steps": steps})
        _DB.add_interaction("assistant", str(result.get("output", "")), context={"original_query": user_input})

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
    """Semantic context retrieval using embeddings (limited to recent pool for speed)."""
    query_vec = get_embedding(user_input)
    if not query_vec:
        # Fallback to recent history if Ollama embeddings unavailable
        return get_recent_history(limit)

    with _LOCK:
        history = _DB.get_recent_history(50)

    scored = []
    for entry in history:
        content = entry.get("content", "")
        past_vec = get_embedding(content)
        if past_vec:
            score = cosine_similarity(query_vec, past_vec)
            scored.append((score, {
                "user_input": content if entry.get("role") == "user" else "",
                "steps": [],
                "result": {"output": content if entry.get("role") == "assistant" else ""},
            }))

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
