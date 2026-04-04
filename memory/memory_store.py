from __future__ import annotations

"""Simple JSON-based memory store for interactions and preferences."""

import json
import threading
from pathlib import Path
from typing import Any, Dict, List

MEMORY_PATH = Path(__file__).resolve().parent / "memory.json"
_LOCK = threading.Lock()


def _load() -> Dict[str, Any]:
    if not MEMORY_PATH.exists():
        return {"interactions": [], "preferences": {}}
    try:
        with MEMORY_PATH.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {"interactions": [], "preferences": {}}


def _save(data: Dict[str, Any]) -> None:
    MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = MEMORY_PATH.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    tmp.replace(MEMORY_PATH)


def save_interaction(user_input: str, steps: List[Dict[str, Any]], result: Dict[str, Any]) -> None:
    with _LOCK:
        data = _load()
        interactions = data.get("interactions", [])
        interactions.append(
            {
                "user_input": user_input,
                "steps": steps,
                "result": result,
            }
        )
        data["interactions"] = interactions[-50:]  # keep last 50
        _save(data)


def get_recent_history(limit: int = 5) -> List[Dict[str, Any]]:
    with _LOCK:
        data = _load()
        return list(data.get("interactions", [])[-limit:])


def get_frequent_commands(limit: int = 5) -> List[Dict[str, Any]]:
    counts: Dict[str, int] = {}
    with _LOCK:
        data = _load()
        for inter in data.get("interactions", []):
            for step in inter.get("steps", []):
                action = step.get("action", "unknown")
                counts[action] = counts.get(action, 0) + 1
    sorted_items = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    return [{"action": action, "count": count} for action, count in sorted_items[:limit]]


def store_preference(key: str, value: Any) -> None:
    with _LOCK:
        data = _load()
        prefs = data.get("preferences", {})
        prefs[key] = value
        data["preferences"] = prefs
        _save(data)
