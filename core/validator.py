from __future__ import annotations

"""Validation pipeline for actions and parameters."""

from pathlib import Path
from typing import Any, Dict

import config
from utils.logger import get_logger

logger = get_logger(__name__)


FILE_ACTIONS = {
    "list_files",
    "create_folder",
    "delete_file",
    "move_file",
    "copy_file",
    "rename_file",
    "search_file",
    "file_info",
}


def _is_safe_path(path: str) -> bool:
    try:
        resolved = Path(path).expanduser().resolve()
    except Exception:
        return False
    for root in config.SAFE_DIRECTORIES:
        try:
            root_path = Path(root).expanduser().resolve()
            if resolved == root_path or resolved.is_relative_to(root_path):
                return True
        except Exception:
            continue
    return False


def validate_action(action: str, target: str, extra: Dict[str, Any]) -> Dict[str, Any]:
    from core.action_registry import ACTION_REGISTRY  # Imported lazily to avoid circular import

    if action not in ACTION_REGISTRY:
        return {"ok": False, "reason": f"Unsupported action: {action}"}

    if action in FILE_ACTIONS and target:
        if not _is_safe_path(target):
            return {"ok": False, "reason": f"Unsafe path: {target}"}

    if action in {"move_file", "copy_file"}:
        src = extra.get("source", "")
        if not src or not _is_safe_path(src):
            return {"ok": False, "reason": f"Unsafe source path: {src or 'missing'}"}
    if action == "rename_file" and not extra.get("new_name"):
        return {"ok": False, "reason": "New name required for rename"}

    return {"ok": True}
