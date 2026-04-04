from __future__ import annotations

"""Lightweight JSON cache for command → action mapping."""

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

import config
from utils.logger import get_logger

logger = get_logger(__name__)

_CACHE_PATH = Path(config.RESPONSE_CACHE_PATH).resolve()


def _load_cache() -> Dict[str, Any]:
    if not _CACHE_PATH.exists():
        return {"entries": {}}
    try:
        with _CACHE_PATH.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to load response cache: %s", exc)
        return {"entries": {}}


def _persist(data: Dict[str, Any]) -> None:
    _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = _CACHE_PATH.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    tmp.replace(_CACHE_PATH)


def _is_fresh(ts: float) -> bool:
    return (time.time() - ts) < config.RESPONSE_CACHE_TTL_S


def get_cached_response(command: str) -> Optional[Dict[str, Any]]:
    """Return cached response if present and fresh."""
    normalized = command.strip().lower()
    data = _load_cache()
    entry = data.get("entries", {}).get(normalized)
    if not entry:
        return None
    ts = entry.get("ts", 0)
    if not _is_fresh(ts):
        return None
    return entry.get("result")


def put_cached_response(command: str, result: Dict[str, Any]) -> None:
    """Cache a response for future identical commands."""
    normalized = command.strip().lower()
    if not normalized or not result:
        return
    data = _load_cache()
    entries = data.get("entries", {})
    entries[normalized] = {"ts": time.time(), "result": result}
    data["entries"] = entries
    _persist(data)
