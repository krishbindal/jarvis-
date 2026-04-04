from __future__ import annotations

"""Simple JSON-based memory store for interactions and preferences."""

import json
import re
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


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z0-9]+", text.lower()))


def get_relevant_context(user_input: str, limit: int = 3) -> List[Dict[str, Any]]:
    """Return up to `limit` past interactions most similar to the current input."""
    query_tokens = _tokenize(user_input)
    if not query_tokens:
        return []

    with _LOCK:
        data = _load()
        interactions = data.get("interactions", [])

    scored: List[tuple[int, Dict[str, Any]]] = []
    for inter in interactions:
        past_input = inter.get("user_input", "")
        step_texts = []
        for step in inter.get("steps", []):
            action = step.get("action", "")
            target = step.get("target", "") or step.get("output", "")
            if action:
                step_texts.append(action)
            if target:
                step_texts.append(str(target))
        haystack = " ".join([past_input] + step_texts)
        tokens = _tokenize(haystack)
        score = len(tokens & query_tokens)
        if score > 0:
            scored.append((score, inter))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [inter for _, inter in scored[:limit]]


def store_preference(key: str, value: Any) -> None:
    with _LOCK:
        data = _load()
        prefs = data.get("preferences", {})
        prefs[key] = value
        data["preferences"] = prefs
        _save(data)
