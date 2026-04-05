from __future__ import annotations

"""
Central Action Registry with Self-Healing Execution Engine.

Phase 4:  Centralized execution logic
Phase 7:  Error handling — wrap all executors in try/except
Phase 10: Self-healing — retry with fallback chain
Phase 14: Clean architecture — separate executor from parser
"""

import os
import subprocess
import logging
import traceback
from pathlib import Path
from typing import Any, Dict, Optional

from skills import execute_skill

from core.mcp_hub import get_mcp_hub

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
    run_system_check,
    kill_process,
)

logger = logging.getLogger("jarvis.executor")


# ───────────────────────────────────────────────────────────
# Dynamic Handlers
# ───────────────────────────────────────────────────────────

def _chat_handler(target: str) -> Dict[str, Any]:
    """Handle conversational/greeting messages with varied responses."""
    _RESPONSES = {
        "hi":            "Hey there! How can I help?",
        "hello":         "Hello! What can I do for you?",
        "hey":           "Hey! I'm listening.",
        "yo":            "Yo! What's up?",
        "hola":          "Hola! How can I assist you?",
        "how are you":   "I'm running at peak performance! What do you need?",
        "how r u":       "Doing great! What can I do for you?",
        "thanks":        "You're welcome! Anything else?",
        "thank you":     "Happy to help!",
        "bye":           "See you later! Just call me when you need me.",
        "goodbye":       "Goodbye! I'll be here when you need me.",
        "see you":       "See you! I'll be ready when you're back.",
        "good morning":  "Good morning! Ready to get things done.",
        "good evening":  "Good evening! How can I help?",
        "good afternoon":"Good afternoon! What's on the agenda?",
        "good night":    "Good night! Sweet dreams.",
        "sup":           "Not much! What do you need?",
        "what's up":     "All systems nominal! How can I help?",
    }
    msg = _RESPONSES.get(target, "Hi! I'm Jarvis, your Dexter Copilot. How can I help you?")
    return {"success": True, "status": "success", "message": msg, "output": "greeting"}


def _system_check_handler(target: str) -> Dict[str, Any]:
    """Execute the Sentinel Protocol (Master Diagnostic)."""
    try:
        res = subprocess.check_output("python jarvis_master_check.py", shell=True, stderr=subprocess.STDOUT, text=True)
        # Parse for the "STATUS" line to give a clean message
        status_line = [line for line in res.split('\n') if "STATUS:" in line]
        msg = status_line[0] if status_line else "Diagnostic completed."
        return {"success": True, "status": "success", "message": f"Sir, I have performed a full system check. {msg}", "output": res}
    except Exception as e:
        return {"success": False, "status": "error", "message": f"Diagnostic failure: {e}"}


def _open_dynamic_handler(target: str, extra: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Universal dynamic open handler with self-healing fallback chain (Phase 10).

    Fallback order:
        1. Specific app launch (start chrome "URL")
        2. System default handler (start "" "URL")
        3. os.startfile() as last resort
    """
    extra = extra or {}
    app = extra.get("app", "")
    resolved_type = extra.get("resolved_type", "url")

    attempts = []

    # ── Attempt 1: Open with specified app ────────────────────
    if app:
        try:
            logger.info("[EXEC] Attempt 1: Opening %s '%s' in '%s'", resolved_type, target, app)
            if app in ("chrome", "msedge", "firefox", "brave", "opera"):
                subprocess.Popen(f'start {app} "{target}"', shell=True)
            elif app in ("code",):
                subprocess.Popen(f'code "{target}"', shell=True)
            elif app in ("explorer",):
                subprocess.Popen(f'explorer "{target}"', shell=True)
            else:
                subprocess.Popen(f'start {app} "{target}"', shell=True)

            return {"success": True, "status": "success",
                    "message": f"Opening {target} in {app}", "output": target}
        except Exception as exc:
            attempts.append(f"App launch failed ({app}): {exc}")
            logger.warning("[EXEC] Attempt 1 failed: %s", exc)

    # ── Attempt 2: System default (start "" "target") ─────────
    try:
        logger.info("[EXEC] Attempt 2: Opening '%s' with system default", target)
        subprocess.Popen(f'start "" "{target}"', shell=True)
        return {"success": True, "status": "success",
                "message": f"Opening {target}", "output": target}
    except Exception as exc:
        attempts.append(f"System start failed: {exc}")
        logger.warning("[EXEC] Attempt 2 failed: %s", exc)

    # ── Attempt 3: os.startfile fallback ──────────────────────
    try:
        logger.info("[EXEC] Attempt 3: os.startfile fallback for '%s'", target)
        os.startfile(target)
        return {"success": True, "status": "success",
                "message": f"Opened {target} (fallback)", "output": target}
    except Exception as exc:
        attempts.append(f"os.startfile failed: {exc}")
        logger.error("[EXEC] All 3 attempts failed for '%s': %s", target, attempts)

    return {
        "success": False, "status": "error",
        "message": f"Failed to open {target} after 3 attempts",
        "output": "; ".join(attempts),
    }


def _open_url_handler(target: str) -> Dict[str, Any]:
    """Legacy compat: open URL with system default."""
    return _open_dynamic_handler(target, extra={"resolved_type": "url"})


def _open_folder_handler(target: str) -> Dict[str, Any]:
    """Open a folder with self-healing fallback."""
    path = Path(target).expanduser().resolve()
    try:
        if path.exists():
            os.startfile(str(path))
        else:
            subprocess.Popen(f'explorer "{path}"', shell=True)
        return {"success": True, "status": "success",
                "message": f"Opening folder: {path}", "output": str(path)}
    except Exception as exc:
        logger.warning("[EXEC] Folder open failed, trying explorer: %s", exc)
        try:
            subprocess.Popen(f'explorer "{path}"', shell=True)
            return {"success": True, "status": "success",
                    "message": f"Opening folder: {path} (fallback)", "output": str(path)}
        except Exception as exc2:
            return {"success": False, "status": "error", "message": str(exc2)}


# ───────────────────────────────────────────────────────────
# Safe Executor Wrapper (Phase 7 — Error Handling)
# ───────────────────────────────────────────────────────────

def _safe_exec(func, *args, **kwargs) -> Dict[str, Any]:
    """Wrap any executor function in try/except with structured error info."""
    try:
        return func(*args, **kwargs)
    except Exception as exc:
        logger.error("[EXEC] Action failed: %s\n%s", exc, traceback.format_exc())
        return {
            "success": False, "status": "error",
            "message": f"Execution failed: {exc}",
            "output": traceback.format_exc(),
        }


# ───────────────────────────────────────────────────────────
# Action Registry
# ───────────────────────────────────────────────────────────

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
    # Apps & URLs
    "open_app": open_app,
    "open_url": _open_url_handler,
    "open_folder": _open_folder_handler,
    "open_dynamic": None,  # Routed specially
    "kill_process": kill_process,
    # System
    "media_control": media_control,
    "power_state": power_state,
    "capture_screen": capture_screen,
    "quick_search": quick_search,
    # Conversation
    "chat": _chat_handler,
    "system_check": _system_check_handler,
    "set_personality": lambda target: __import__("memory.personality", fromlist=["set_personality_handler"]).set_personality_handler(target),
}


# ───────────────────────────────────────────────────────────
# Executor (Phase 4 + Phase 7 + Phase 10)
# ───────────────────────────────────────────────────────────

def execute_action(
    action: str,
    target: str = "",
    extra: Optional[Dict[str, Any]] = None,
    previous_result: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Execute a routed action with plugin system support and fallback logic."""
    extra = extra or {}
    
    # ── Input Sanitization (Phase 32) ────────────────────────
    # Some AI providers hallucinate argument names in the target string
    if target:
        # e.g. "name=chrome" -> "chrome", "app=spotify" -> "spotify"
        if "=" in target and not target.startswith(("http", "www", "/")):
            logger.warning(f"[EXEC] Sanitizing hallucinated target: {target}")
            target = target.split("=")[-1].strip("'\" ")
        
        # Clean common punctuation injected by AI or STT
        target = target.strip(" .!,?")

    logger.info(f"[EXEC] action={action} target='{target}'")

    if action.startswith("mcp:"):
        hub = get_mcp_hub()
        return _safe_exec(hub.call_tool, action, extra)

    # ── 1.5 Skill Handlers (Phase 16) ───────────────────────
    if action.startswith("skill:"):
        skill_name = action.replace("skill:", "")
        logger.info(f"[EXEC] Routing to skill: {skill_name}")
        return _safe_exec(execute_skill, skill_name, target, extra)

    # ── 2. Special Handlers ──────────────────────────────────
    if action == "open_dynamic":
        return _safe_exec(_open_dynamic_handler, target, extra)

    # ── 3. Registry Checks ───────────────────────────────────
    func = ACTION_REGISTRY.get(action)
    if not func:
        logger.error(f"[EXEC] Unsupported action: {action}")
        return {"success": False, "status": "error", "message": f"Unsupported action: {action}"}

    # ── Route with proper argument shapes ─────────────────────
    if action == "create_folder":
        return _safe_exec(func, target, extra.get("path"))
    if action in ("move_file", "copy_file"):
        return _safe_exec(func, extra.get("source", ""), target)
    if action == "rename_file":
        return _safe_exec(func, target, extra.get("new_name", ""))
    if action == "search_file":
        return _safe_exec(func, target, extra.get("root_path", ""))
    if action == "trigger_n8n":
        data = dict(extra)
        if previous_result and "previous_output" not in data:
            data["previous_output"] = previous_result.get("output", previous_result)
        return _safe_exec(func, target or action, data)
    return _safe_exec(func, target)
