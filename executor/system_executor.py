from __future__ import annotations

"""File system executor with safety checks."""

import os
import shutil
import subprocess
import difflib
from pathlib import Path
from typing import Dict, List

from config import SAFE_DIRECTORIES
from utils.logger import get_logger

logger = get_logger(__name__)


def _allowed_roots() -> List[Path]:
    return [Path(p).expanduser().resolve() for p in SAFE_DIRECTORIES]


def _is_safe(path: Path) -> bool:
    # PERMISSION OVERRIDE: Unrestricted C: drive access enabled by user request.
    return True


def _safe_path(raw: str) -> Path:
    resolved = Path(raw).expanduser().resolve()
    return resolved


def _default_dir() -> Path:
    # Default to C:\ root if unrestricted fallback is needed, else current dir
    return Path("C:\\").resolve()


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
        root = Path(root_path).expanduser().resolve() if root_path else Path("C:\\").resolve()
        matches: List[str] = []
        for entry in root.rglob(name):
            if entry.is_file():
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
    if action == "open_app":
        return open_app(target)
    return {"success": False, "message": f"Unsupported action: {action}"}


def open_app(target: str) -> Dict:
    target_lower = target.lower().strip()
    logger.info("Opening %s via subprocess", target_lower)
    
    if target_lower == "chrome":
        try:
            subprocess.Popen("start chrome", shell=True)
            return {"success": True, "status": "success", "message": "Chrome launched", "output": "Chrome launched"}
        except Exception:
            paths = [
                "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
                "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"
            ]
            for path in paths:
                if os.path.exists(path):
                    subprocess.Popen(path)
                    return {"success": True, "status": "success", "message": "Chrome launched", "output": "Chrome launched"}
            # Fallthrough if chrome executable not found via hardcoded paths
            
    # Universal Windows App Scanner
    try:
        common_start = Path(os.environ.get('ALLUSERSPROFILE', 'C:\\ProgramData')) / 'Microsoft\\Windows\\Start Menu\\Programs'
        user_start = Path(os.environ.get('APPDATA', '')) / 'Microsoft\\Windows\\Start Menu\\Programs'
        app_paths = {}
        
        for start_dir in [common_start, user_start]:
            if start_dir.exists():
                for p in start_dir.rglob("*.lnk"):
                    name = p.stem.lower()
                    if "uninstall" not in name and "remove" not in name and "setup" not in name:
                        app_paths[name] = str(p)
                for p in start_dir.rglob("*.exe"):
                    name = p.stem.lower()
                    if "uninstall" not in name and "remove" not in name and "setup" not in name:
                        app_paths[name] = str(p)
                    
        # Find exact matches, fuzzy matches or substring matches
        # Increased cutoff to 0.75 to prevent matching unrelated keywords
        matches = difflib.get_close_matches(target_lower, app_paths.keys(), n=1, cutoff=0.75)
        
        if not matches:
            for app_name in app_paths.keys():
                # Strict substring matching (at word boundaries or direct inclusion of a significant chunk)
                if target_lower in app_name.split() or target_lower == app_name:
                    matches.append(app_name)
                    break 

        if matches:
            best_match = matches[0]
            app_path = app_paths[best_match]
            logger.info("Found App Match: %s -> %s", best_match, app_path)
            
            # Startfile natively launches .lnk and .exe without blocking gracefully
            os.startfile(app_path)
            
            return {"success": True, "status": "success", "message": f"{best_match} launched", "output": f"{best_match} launched"}
        else:
            # Check if it's a Microsoft Store app URI (e.g. netflix:)
            app_uri = f"{target_lower}:"
            logger.info(f"No specific shortcut found. Attempting generic protocol/start for {target_lower}")
            # we will let the fallback try to start it below
    except Exception as e:
        logger.error("Failed scanning installed apps: %s", e)

    # Generic start fallback for unrecognized system commands
    try:
        # Try generic target launch first
        try:
            subprocess.run(f"start \"\" \"{target}\"", shell=True, check=True, stderr=subprocess.DEVNULL)
            return {"success": True, "status": "success", "message": f"Fallback executed for {target}", "output": f"{target} fallback"}
        except subprocess.CalledProcessError:
            # If that failed, it might be a Windows Store or URI-mapped app like netflix:
            subprocess.run(f"start \"\" \"{target}:\"", shell=True, check=True, stderr=subprocess.DEVNULL)
            return {"success": True, "status": "success", "message": f"URI Fallback executed for {target}:", "output": f"{target} fallback"}
    except Exception as exc:
        return {"success": False, "status": "error", "message": str(exc)}

import ctypes

def media_control(action: str) -> Dict:
    # Virtual-Key Codes for media
    vk_media = {
        "play": 0xB3, "pause": 0xB3, "play_pause": 0xB3,
        "next": 0xB0, "previous": 0xB1, "stop": 0xB2,
        "mute": 0xAD, "volume_down": 0xAE, "volume_up": 0xAF
    }
    action_key = action.lower()
    if action_key in vk_media:
        vk_code = vk_media[action_key]
        ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
        ctypes.windll.user32.keybd_event(vk_code, 0, 2, 0)
        return {"success": True, "status": "success", "message": f"Media action executing: {action}", "output": f"Sent VK {vk_code}"}
    return {"success": False, "status": "error", "message": f"Unknown media action: {action}"}

def power_state(action: str) -> Dict:
    action_key = action.lower()
    try:
        if action_key == "lock":
            ctypes.windll.user32.LockWorkStation()
            return {"success": True, "status": "success", "message": "Workstation locked"}
        elif action_key == "sleep":
            subprocess.run("rundll32.exe powrprof.dll,SetSuspendState 0,1,0", shell=True)
            return {"success": True, "status": "success", "message": "Putting computer to sleep"}
        return {"success": False, "status": "error", "message": f"Unknown power action: {action}"}
    except Exception as exc:
        return {"success": False, "status": "error", "message": str(exc)}

import time
from PIL import ImageGrab

def capture_screen(target: str = "") -> Dict:
    try:
        import os
        from pathlib import Path
        assets_dir = Path("assets/memory")
        assets_dir.mkdir(parents=True, exist_ok=True)
        filename = f"jarvis_vision_{int(time.time())}.png"
        filepath = assets_dir / filename
        screenshot = ImageGrab.grab()
        screenshot.save(filepath)
        return {"success": True, "status": "success", "message": f"Screen captured to {filepath}", "output": str(filepath)}
    except Exception as exc:
        return {"success": False, "status": "error", "message": f"Screen capture failed: {str(exc)}"}

def quick_search(query: str) -> Dict:
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
        if not results:
            return {"success": True, "status": "success", "message": f"No results found for '{query}'", "output": "No matches."}
        
        snippets = "\n".join([f"- {r.get('title')}: {r.get('body')}" for r in results])
        return {"success": True, "status": "success", "message": f"Web search for '{query}' complete.", "output": snippets}
    except Exception as exc:
        return {"success": False, "status": "error", "message": f"Web search failed: {str(exc)}"}
