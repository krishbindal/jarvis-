from __future__ import annotations

"""File system executor with safety checks."""

import os
import platform
import shutil
import subprocess
import webbrowser
from pathlib import Path
from typing import Dict, List

from config import SAFE_DIRECTORIES
from utils.logger import get_logger

logger = get_logger(__name__)


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


def _default_dir() -> Path:
    candidates = [
        Path("~/Downloads").expanduser(),
        Path("~/Documents").expanduser(),
        Path(".").resolve(),
    ]
    for cand in candidates:
        try:
            if cand.exists():
                resolved = cand.resolve()
                if _is_safe(resolved):
                    return resolved
        except Exception:
            continue
    return Path(".").resolve()


def open_app(target: str) -> Dict:
    if not target:
        return {"success": False, "status": "error", "message": "No application specified"}
    try:
        logger.info("Opening application: %s", target)
        system = platform.system().lower()
        if system == "windows":
            subprocess.Popen(["start", "", target], shell=True)
        elif system == "darwin":
            subprocess.Popen(["open", "-a", target])
        else:
            subprocess.Popen([target])
        return {"success": True, "status": "success", "message": f"Launched {target}", "output": target}
    except FileNotFoundError:
        logger.error("Application not found: %s", target)
        return {"success": False, "status": "error", "message": f"Application not found: {target}"}
    except Exception as exc:  # noqa: BLE001
        logger.error("open_app failed: %s", exc)
        return {"success": False, "status": "error", "message": str(exc)}


def open_url(url: str) -> Dict:
    try:
        webbrowser.open(url, new=2, autoraise=True)
        logger.info("Opening URL: %s", url)
        return {"success": True, "status": "success", "message": f"Opened {url}", "output": url}
    except Exception as exc:  # noqa: BLE001
        logger.error("open_url failed for %s: %s", url, exc)
        return {"success": False, "status": "error", "message": f"Failed to open {url}: {exc}"}


def media_control(target: str) -> Dict:
    # Placeholder: real media controls are platform-specific; here we acknowledge the request.
    logger.info("Media control requested: %s", target)
    return {"success": True, "status": "success", "message": f"Media control: {target}", "output": target}


def power_state(target: str) -> Dict:
    logger.info("Power state request: %s", target)
    return {"success": True, "status": "success", "message": f"Power state change requested: {target}", "output": target}


def capture_screen(_: str = "") -> Dict:
    try:
        import pyautogui

        output_dir = Path("assets/memory")
        output_dir.mkdir(parents=True, exist_ok=True)
        dest = output_dir / "last_screen.png"
        screenshot = pyautogui.screenshot()
        screenshot.save(dest)
        logger.info("Captured screen to %s", dest)
        return {"success": True, "status": "success", "message": "Screen captured", "output": str(dest)}
    except Exception as exc:  # noqa: BLE001
        logger.error("Screen capture failed: %s", exc)
        return {"success": False, "status": "error", "message": f"Screen capture failed: {exc}"}


def quick_search(query: str) -> Dict:
    if not query:
        return {"success": False, "status": "error", "message": "No search query provided"}
    url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
    logger.info("Quick search: %s", query)
    return open_url(url)


def list_files(path: str) -> Dict:
    try:
        target_path = path or str(_default_dir())
        target = _safe_path(target_path)
        if not target.exists() or not target.is_dir():
            return {"success": False, "status": "error", "message": f"Not a directory: {target}"}
        logger.info("Listing files in %s", target)
        items = sorted([p.name for p in target.iterdir()])
        preview = ", ".join(items[:5])
        suffix = "" if not preview else f": {preview}"
        return {
            "success": True,
            "status": "success",
            "message": f"Found {len(items)} items in {target}{suffix}",
            "data": items,
            "output": items,
        }
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "status": "error", "message": str(exc)}


def create_folder(name: str, path: str | None = None) -> Dict:
    try:
        base = _safe_path(path or str(_default_dir()))
        target = (base / name).resolve()
        if not _is_safe(target):
            raise ValueError(f"Path not allowed: {target}")
        target.mkdir(parents=True, exist_ok=True)
        logger.info("Folder ensured at %s", target)
        return {"success": True, "status": "success", "message": f"Folder ensured at {target}", "output": str(target)}
    except Exception as exc:  # noqa: BLE001
        logger.error("Create folder failed for %s in %s: %s", name, path, exc)
        return {"success": False, "status": "error", "message": str(exc)}


def delete_file(path: str) -> Dict:
    try:
        target = _safe_path(path)
        if not target.exists():
            return {"success": False, "status": "error", "message": f"File not found: {target}"}
        if target.is_dir():
            return {"success": False, "status": "error", "message": "Refusing to delete directory."}
        target.unlink()
        logger.info("Deleted file %s", target)
        return {"success": True, "status": "success", "message": f"Deleted {target}", "output": str(target)}
    except Exception as exc:  # noqa: BLE001
        logger.error("Delete file failed for %s: %s", path, exc)
        return {"success": False, "status": "error", "message": str(exc)}


def move_file(src: str, dest: str) -> Dict:
    try:
        source_path = _safe_path(src)
        dest_path = _safe_path(dest)
        if dest_path.is_dir():
            dest_path = dest_path / source_path.name
        shutil.move(str(source_path), str(dest_path))
        logger.info("Moved %s to %s", source_path, dest_path)
        return {"success": True, "status": "success", "message": f"Moved to {dest_path}", "output": str(dest_path)}
    except Exception as exc:  # noqa: BLE001
        logger.error("Move file failed from %s to %s: %s", src, dest, exc)
        return {"success": False, "status": "error", "message": str(exc)}


def copy_file(src: str, dest: str) -> Dict:
    try:
        source_path = _safe_path(src)
        dest_path = _safe_path(dest)
        if dest_path.is_dir():
            dest_path = dest_path / source_path.name
        shutil.copy2(str(source_path), str(dest_path))
        logger.info("Copied %s to %s", source_path, dest_path)
        return {"success": True, "status": "success", "message": f"Copied to {dest_path}", "output": str(dest_path)}
    except Exception as exc:  # noqa: BLE001
        logger.error("Copy file failed from %s to %s: %s", src, dest, exc)
        return {"success": False, "status": "error", "message": str(exc)}


def rename_file(path: str, new_name: str) -> Dict:
    try:
        source = _safe_path(path)
        dest = source.with_name(new_name)
        if not _is_safe(dest):
            raise ValueError(f"Path not allowed: {dest}")
        source.rename(dest)
        logger.info("Renamed %s to %s", source, dest)
        return {
            "success": True,
            "status": "success",
            "message": f"Renamed to {dest.name}",
            "data": str(dest),
            "output": str(dest),
        }
    except Exception as exc:  # noqa: BLE001
        logger.error("Rename file failed for %s to %s: %s", path, new_name, exc)
        return {"success": False, "status": "error", "message": str(exc)}


def search_file(name: str, root_path: str) -> Dict:
    try:
        root = _safe_path(root_path or str(_default_dir()))
        matches: List[str] = []
        for entry in root.rglob(name):
            if entry.is_file() and _is_safe(entry):
                matches.append(str(entry))
            if len(matches) >= 25:
                break
        logger.info("Search for %s in %s found %d matches", name, root, len(matches))
        preview = ", ".join([Path(m).name for m in matches[:5]])
        suffix = "" if not preview else f": {preview}"
        return {
            "success": True,
            "status": "success",
            "message": f"Found {len(matches)} match(es){suffix}",
            "data": matches,
            "output": matches,
        }
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "status": "error", "message": str(exc)}


def file_info(path: str) -> Dict:
    try:
        target = _safe_path(path)
        if not target.exists():
            return {"success": False, "status": "error", "message": f"Path not found: {target}"}
        stat = target.stat()
        info = {
            "path": str(target),
            "size": stat.st_size,
            "modified": stat.st_mtime,
            "is_dir": target.is_dir(),
            "is_file": target.is_file(),
        }
        logger.info("Retrieved file info for %s", target)
        return {"success": True, "status": "success", "message": "File info retrieved.", "data": info, "output": info}
    except Exception as exc:  # noqa: BLE001
        logger.error("File info failed for %s: %s", path, exc)
        return {"success": False, "status": "error", "message": str(exc)}


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
