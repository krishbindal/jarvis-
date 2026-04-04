from __future__ import annotations

"""Store for macros and reusable workflows."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import config
from utils.logger import get_logger

logger = get_logger(__name__)

_MACRO_PATH = Path(config.MACRO_PATH).resolve()
_WORKFLOW_PATH = Path(config.WORKFLOW_MEMORY_PATH).resolve()


def _load_json(path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to load %s: %s", path, exc)
        return default


def _save_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    tmp.replace(path)


def load_macros() -> Dict[str, List[Any]]:
    data = _load_json(_MACRO_PATH, {"macros": {}})
    return data.get("macros", {})


def save_macros(macros: Dict[str, List[Any]]) -> None:
    _save_json(_MACRO_PATH, {"macros": macros})


def resolve_macro(command: str) -> Optional[List[Any]]:
    normalized = command.strip().lower()
    if not normalized:
        return None
    macros = load_macros()
    for name, steps in macros.items():
        if normalized == name.lower():
            return steps
    return None


def record_workflow(name: str, steps: List[Dict[str, Any]]) -> None:
    """Persist a named workflow for reuse."""
    workflows = _load_json(_WORKFLOW_PATH, {"workflows": {}})
    stored = workflows.get("workflows", {})
    stored[name] = steps
    workflows["workflows"] = stored
    _save_json(_WORKFLOW_PATH, workflows)


def get_workflows() -> Dict[str, List[Dict[str, Any]]]:
    workflows = _load_json(_WORKFLOW_PATH, {"workflows": {}})
    return workflows.get("workflows", {})
