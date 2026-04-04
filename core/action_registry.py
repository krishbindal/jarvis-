from __future__ import annotations

"""Central registry for executable actions."""

import os
import subprocess
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from executor.conversion_executor import convert_to_mp3, convert_to_pdf
from executor.download_executor import download_file, download_video
from executor.n8n_executor import trigger_workflow
from executor.system_executor import (
    copy_file,
    create_folder,
    delete_file,
    file_info,
    list_files,
    move_file,
    rename_file,
    search_file,
    open_app,
    media_control,
    power_state,
    capture_screen,
    quick_search,
)

logger = logging.getLogger("jarvis.action_registry")


# ───────────────────────────────────────────────
# Dynamic Handlers
# ───────────────────────────────────────────────

def _chat_handler(target: str) -> Dict[str, Any]:
    """Handle conversational/greeting messages."""
    _RESPONSES = {
        "hi":  "Hey there! How can I help?",
        "hello":  "Hello! What can I do for you?",
        "hey":  "Hey! I'm listening.",
        "how are you": "I'm running at peak performance! What do you need?",
        "thanks": "You're welcome! Anything else?",
        "thank you": "Happy to help!",
        "bye": "See you later! Just call me when you need me.",
        "goodbye": "Goodbye! I'll be here when you need me.",
        "good morning": "Good morning! Ready to get things done.",
        "good evening": "Good evening! How can I help?",
        "good afternoon": "Good afternoon! What's on the agenda?",
        "good night": "Good night! Sweet dreams.",
    }
    msg = _RESPONSES.get(target, "Hi! I'm Jarvis, your Dexter Copilot. How can I help you?")
    return {"success": True, "status": "success", "message": msg, "output": "greeting"}


def _open_dynamic_handler(target: str, extra: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Universal dynamic open handler.
    
    Handles:
        - URLs in specific browsers: start chrome "https://..."
        - Files in specific editors:  code "report.pdf"
        - Generic URL / file open:    start "" "https://..."
    
    Args:
        target: The resolved URL, file path, or folder path
        extra:  { "app": "chrome", "resolved_type": "url" | "file" }
    """
    extra = extra or {}
    app = extra.get("app", "")
    resolved_type = extra.get("resolved_type", "url")

    try:
        if app:
            logger.info(f"[DYNAMIC] Opening {resolved_type} '{target}' in app '{app}'")
            # Build the launch command
            if app in ("chrome", "msedge", "firefox", "brave"):
                # Browser → pass URL as argument
                subprocess.Popen(f'start {app} "{target}"', shell=True)
            elif app in ("code",):
                # VS Code → use code CLI
                subprocess.Popen(f'code "{target}"', shell=True)
            elif app in ("explorer",):
                # Explorer → open folder / file location
                subprocess.Popen(f'explorer "{target}"', shell=True)
            elif app in ("notepad", "notepad++"):
                subprocess.Popen(f'start {app} "{target}"', shell=True)
            else:
                # Generic: try start <app> "<target>"
                subprocess.Popen(f'start {app} "{target}"', shell=True)
        else:
            logger.info(f"[DYNAMIC] Opening '{target}' with system default")
            subprocess.Popen(f'start "" "{target}"', shell=True)

        return {
            "success": True, "status": "success",
            "message": f"Opening {target}" + (f" in {app}" if app else ""),
            "output": target,
        }
    except Exception as exc:
        logger.error(f"[DYNAMIC] Failed to open {target}: {exc}")
        # Fallback: try system default
        try:
            os.startfile(target)
            return {"success": True, "status": "success",
                    "message": f"Opened {target} (fallback)", "output": target}
        except Exception as exc2:
            return {"success": False, "status": "error", "message": str(exc2)}


def _open_url_handler(target: str) -> Dict[str, Any]:
    """Open a URL in the default browser (legacy compat)."""
    return _open_dynamic_handler(target, extra={"resolved_type": "url"})


def _open_folder_handler(target: str) -> Dict[str, Any]:
    """Open a folder in Windows Explorer."""
    try:
        path = Path(target).expanduser().resolve()
        if path.exists():
            os.startfile(str(path))
        else:
            subprocess.Popen(f'explorer "{path}"', shell=True)
        return {"success": True, "status": "success",
                "message": f"Opening folder: {path}", "output": str(path)}
    except Exception as exc:
        return {"success": False, "status": "error", "message": str(exc)}


# ───────────────────────────────────────────────
# Action Registry
# ───────────────────────────────────────────────

ACTION_REGISTRY = {
    # File operations
    "list_files": list_files,
    "create_folder": create_folder,
    "delete_file": delete_file,
    "move_file": move_file,
    "copy_file": copy_file,
    "rename_file": rename_file,
    "search_file": search_file,
    "file_info": file_info,
    # Downloads
    "download_file": download_file,
    "download_video": download_video,
    # Conversions
    "convert_to_mp3": convert_to_mp3,
    "convert_to_pdf": convert_to_pdf,
    # Automation
    "trigger_n8n": trigger_workflow,
    # Apps & URLs (dynamic)
    "open_app": open_app,
    "open_url": _open_url_handler,
    "open_folder": _open_folder_handler,
    "open_dynamic": None,  # Handled specially in execute_action
    # System controls
    "media_control": media_control,
    "power_state": power_state,
    "capture_screen": capture_screen,
    "quick_search": quick_search,
    # Conversation
    "chat": _chat_handler,
}


# ───────────────────────────────────────────────
# Executor
# ───────────────────────────────────────────────

def execute_action(
    action: str,
    target: str = "",
    extra: Optional[Dict[str, Any]] = None,
    previous_result: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Execute a routed action."""
    extra = extra or {}

    # ── Special: open_dynamic (needs target + extra together) ──────
    if action == "open_dynamic":
        return _open_dynamic_handler(target, extra)

    func = ACTION_REGISTRY.get(action)
    if not func:
        return {"success": False, "status": "error", "message": f"Unsupported action: {action}"}

    # ── Route with proper argument shapes ──────────────────────────
    if action == "create_folder":
        return func(target, extra.get("path"))
    if action in ("move_file", "copy_file"):
        return func(extra.get("source", ""), target)
    if action == "rename_file":
        return func(target, extra.get("new_name", ""))
    if action == "search_file":
        return func(target, extra.get("root_path", ""))
    if action == "trigger_n8n":
        data = dict(extra)
        if previous_result and "previous_output" not in data:
            data["previous_output"] = previous_result.get("output", previous_result)
        return func(target or action, data)
    return func(target)
