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

try:
    import pyautogui
    _PYAUTOGUI_ERROR = None
except Exception as exc:  # noqa: BLE001
    pyautogui = None
    _PYAUTOGUI_ERROR = exc

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


def search_file(name: str, root_path: str = "") -> Dict:
    """Fast recursive search using Windows native 'where' command."""
    try:
        # Phase 16: Optimization for low-end PCs
        # Default to user profile to avoid scanning System32/Program Files
        search_root = os.environ.get("USERPROFILE", "C:\\Users")
        if root_path:
            search_root = str(_safe_path(root_path))

        logger.info("[SYSTEM] Fast-searching for '%s' in %s", name, search_root)
        
        # 'where /r <path> <pattern>' is much faster than python's rglob
        # We use *name* to allow partial matching
        cmd = f'where /r "{search_root}" "*{name}*"'
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=20)
        
        matches = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        matches = matches[:25] # Limit results for UI clarity

        if not matches:
             return {"success": True, "status": "success", "message": f"Sir, I couldn't find any files matching '{name}'.", "output": "No matches."}

        preview = ", ".join([Path(m).name for m in matches[:5]])
        suffix = f": {preview}" if preview else ""
        
        return {
            "success": True,
            "status": "success",
            "message": f"Found {len(matches)} match(es){suffix}",
            "data": matches,
            "output": matches,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "status": "timeout", "message": "Search took too long. Try a more specific name."}
    except Exception as exc:
        logger.error("[SYSTEM] Search failed: %s", exc)
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
    if action == "kill_process":
        return kill_process(target)
    return {"success": False, "message": f"Unsupported action: {action}"}


def kill_process(target: str) -> Dict:
    """Terminate a running process by name or PID."""
    if not target:
        return {"success": False, "status": "error", "message": "No process name specified."}

    target_clean = target.lower().strip().replace(".exe", "")
    
    # Safety: Do not kill explorer.exe unless the user is very specific, 
    # as it restarts the taskbar/desktop and looks like a crash.
    if target_clean == "explorer":
        return {"success": False, "status": "protected", "message": "Sir, I cannot terminate Explorer as it would crash the Windows shell."}

    logger.info("Jarvis is terminating process: %s", target_clean)
    
    try:
        # Use taskkill /F (Force) /IM (Image Name) /T (Tree)
        cmd = f'taskkill /F /IM "{target_clean}.exe" /T'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            return {"success": True, "status": "success", "message": f"Sir, I have terminated {target_clean}.", "output": result.stdout}
        elif "not found" in result.stderr.lower():
            # Try without .exe
            cmd_alt = f'taskkill /F /IM "{target_clean}" /T'
            result_alt = subprocess.run(cmd_alt, shell=True, capture_output=True, text=True)
            if result_alt.returncode == 0:
                return {"success": True, "status": "success", "message": f"Sir, I have terminated {target_clean}.", "output": result_alt.stdout}
            
            return {"success": False, "status": "not_running", "message": f"Sir, {target_clean} is not currently running.", "output": result.stderr}
        else:
            return {"success": False, "status": "error", "message": f"Failed to kill {target_clean}: {result.stderr}", "output": result.stderr}
    except Exception as exc:
        return {"success": False, "status": "error", "message": str(exc)}


def open_app(target: str) -> Dict:
    # Aggressively strip punctuation like dots injected by the AI or STT
    target_lower = target.lower().strip(" .!,?")
    
    # Phase 16: Native Start Menu trigger
    if target_lower == "start" or target_lower == "start menu":
        logger.info("[SYSTEM] Triggering native Start Menu (Win key)")
        if not pyautogui:
            return {"success": False, "status": "error", "message": f"pyautogui unavailable: {_PYAUTOGUI_ERROR}"}
        pyautogui.press('win')
        return {"success": True, "status": "success", "message": "Opening Start Menu", "output": "WIN_KEY"}

    logger.info("Opening %s via system executor", target_lower)
    
    # Special Case: Chrome
    if target_lower == "chrome":
        try:
            subprocess.Popen("start chrome", shell=True)
            return {"success": True, "status": "success", "message": "Chrome launched", "output": "Chrome launched"}
        except Exception:
            pass

    # Special Case: Native Store Apps / URIs
    uri_map = {
        "whatsapp": "whatsapp:",
        "instagram": "instagram:",
        "spotify": "spotify:",
        "netflix": "netflix:",
        "messenger": "ms-messenger:"
    }
    
    if target_lower in uri_map:
        requested_uri = uri_map[target_lower]
        logger.info(f"Target found in URI map: {target_lower} -> {requested_uri}")
        try:
            subprocess.run(f'start "" "{requested_uri}"', shell=True, check=True)
            return {"success": True, "status": "success", "message": f"{target_lower} launched (native)", "output": requested_uri}
        except Exception as e:
            logger.warning(f"URI launch failed for {requested_uri}, falling back to shortcut scan: {e}")

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
                    
        # Find exact matches or substring matches
        matches = difflib.get_close_matches(target_lower, app_paths.keys(), n=1, cutoff=0.75)
        
        if not matches:
            for app_name in app_paths.keys():
                if target_lower == app_name or target_lower in app_name.split():
                    matches.append(app_name)
                    break 

        if matches:
            best_match = matches[0]
            app_path = app_paths[best_match]
            logger.info("Found App Match: %s -> %s", best_match, app_path)
            os.startfile(app_path)
            return {"success": True, "status": "success", "message": f"{best_match} launched", "output": f"{best_match} launched"}
        
    except Exception as e:
        logger.error("Failed scanning installed apps: %s", e)

    # Generic start fallback
    try:
        # Final attempt: direct shell start (handles URLs or in-PATH executables)
        subprocess.run(f'start "" "{target_lower}"', shell=True, check=True, stderr=subprocess.DEVNULL)
        return {"success": True, "status": "success", "message": f"Launched {target_lower}", "output": target_lower}
    except Exception as exc:
        # Last ditch: try as a URI if not already tried
        if target_lower not in uri_map:
            try:
                subprocess.run(f'start "" "{target_lower}:"', shell=True, check=True, stderr=subprocess.DEVNULL)
                return {"success": True, "status": "success", "message": f"Launched {target_lower} as URI", "output": f"{target_lower}:"}
            except Exception:
                pass
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
import mss
from PIL import Image

def capture_screen(target: str = "") -> Dict:
    """Capture all monitors using mss (more stable than ImageGrab in threads)."""
    try:
        from pathlib import Path
        assets_dir = Path("assets/memory")
        assets_dir.mkdir(parents=True, exist_ok=True)
        filename = f"jarvis_vision_{int(time.time())}.png"
        filepath = assets_dir / filename
        
        with mss.mss() as sct:
            # Capture the combined virtual screen (all monitors)
            screenshot = sct.grab(sct.monitors[0])
            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
            img.save(filepath)
            
        logger.info("[SYSTEM] Screen captured to %s", filepath)
        return {"success": True, "status": "success", "message": f"Screen captured to {filepath}", "output": str(filepath)}
    except Exception as exc:
        logger.error("[SYSTEM] Screen capture failed: %s", exc)
        return {"success": False, "status": "error", "message": f"Screen capture failed: {str(exc)}"}

def run_system_check(target: str = "") -> Dict:
    """Trigger the Sentinel Protocol (Master Diagnostic)."""
    try:
        # We run it via subprocess to ensure a fresh environment
        res = subprocess.check_output(f"python jarvis_master_check.py", shell=True, stderr=subprocess.STDOUT, text=True)
        return {"success": True, "status": "success", "message": "Master Diagnostic complete.", "output": res}
    except Exception as exc:
        return {"success": False, "status": "error", "message": f"Diagnostic tool failed: {str(exc)}"}

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
