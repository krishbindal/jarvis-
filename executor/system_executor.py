from __future__ import annotations

"""File system executor with safety checks."""

import os
import shutil
from pathlib import Path
from typing import Dict, List

SAFE_DIRECTORIES = [
    "C:/Users",
    "D:/Projects",
    "~/Downloads",
]


def _allowed_roots() -> List[Path]:
    return [Path(p).expanduser().resolve() for p in SAFE_DIRECTORIES]


def _is_safe(path: Path) -> bool:
    resolved = path.expanduser().resolve()
    for root in _allowed_roots():
        try:
            if resolved == root or resolved.is_relative_to(root):
                return True
        except ValueError:
            continue
    return False


def _safe_path(raw: str) -> Path:
    resolved = Path(raw).expanduser().resolve()
    if not _is_safe(resolved):
        raise ValueError(f"Path not allowed: {resolved}")
    return resolved


def list_files(path: str) -> Dict:
    try:
        target = _safe_path(path or ".")
        if not target.exists() or not target.is_dir():
            return {"success": False, "message": f"Not a directory: {target}"}
        items = sorted([p.name for p in target.iterdir()])
        return {"success": True, "message": f"Found {len(items)} items in {target}", "data": items}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "message": str(exc)}


def create_folder(name: str, path: str | None = None) -> Dict:
    try:
        base = _safe_path(path or ".")
        target = (base / name).resolve()
        if not _is_safe(target):
            raise ValueError(f"Path not allowed: {target}")
        target.mkdir(parents=True, exist_ok=True)
        return {"success": True, "message": f"Folder ensured at {target}"}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "message": str(exc)}


def delete_file(path: str) -> Dict:
    try:
        target = _safe_path(path)
        if not target.exists():
            return {"success": False, "message": f"File not found: {target}"}
        if target.is_dir():
            return {"success": False, "message": "Refusing to delete directory."}
        target.unlink()
        return {"success": True, "message": f"Deleted {target}"}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "message": str(exc)}


def move_file(src: str, dest: str) -> Dict:
    try:
        source_path = _safe_path(src)
        dest_path = _safe_path(dest)
        if dest_path.is_dir():
            dest_path = dest_path / source_path.name
        shutil.move(str(source_path), str(dest_path))
        return {"success": True, "message": f"Moved to {dest_path}"}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "message": str(exc)}


def copy_file(src: str, dest: str) -> Dict:
    try:
        source_path = _safe_path(src)
        dest_path = _safe_path(dest)
        if dest_path.is_dir():
            dest_path = dest_path / source_path.name
        shutil.copy2(str(source_path), str(dest_path))
        return {"success": True, "message": f"Copied to {dest_path}"}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "message": str(exc)}


def rename_file(path: str, new_name: str) -> Dict:
    try:
        source = _safe_path(path)
        dest = source.with_name(new_name)
        if not _is_safe(dest):
            raise ValueError(f"Path not allowed: {dest}")
        source.rename(dest)
        return {"success": True, "message": f"Renamed to {dest.name}", "data": str(dest)}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "message": str(exc)}


def search_file(name: str, root_path: str) -> Dict:
    try:
        root = _safe_path(root_path or ".")
        matches: List[str] = []
        for entry in root.rglob(name):
            if entry.is_file() and _is_safe(entry):
                matches.append(str(entry))
            if len(matches) >= 25:
                break
        return {"success": True, "message": f"Found {len(matches)} match(es)", "data": matches}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "message": str(exc)}


def file_info(path: str) -> Dict:
    try:
        target = _safe_path(path)
        if not target.exists():
            return {"success": False, "message": f"Path not found: {target}"}
        stat = target.stat()
        info = {
            "path": str(target),
            "size": stat.st_size,
            "modified": stat.st_mtime,
            "is_dir": target.is_dir(),
            "is_file": target.is_file(),
        }
        return {"success": True, "message": "File info retrieved.", "data": info}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "message": str(exc)}


def execute_file_command(action: str, target: str, extra: dict | None = None) -> Dict:
    extra = extra or {}
    if action == "list_files":
        return list_files(target)
    if action == "create_folder":
        return create_folder(target, extra.get("path"))
    if action == "delete_file":
        return delete_file(target)
    if action == "move_file":
        return move_file(extra.get("source", ""), target)
    if action == "copy_file":
        return copy_file(extra.get("source", ""), target)
    if action == "rename_file":
        return rename_file(target, extra.get("new_name", ""))
    if action == "search_file":
        return search_file(target, extra.get("root_path", ""))
    if action == "file_info":
        return file_info(target)
    return {"success": False, "message": f"Unsupported action: {action}"}
