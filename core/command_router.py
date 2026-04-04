from __future__ import annotations

"""Simple rule-based command router for Phase 2."""

import re
from typing import Dict

_STOP_WORDS = ("please", "jarvis", "hey jarvis")


def _normalize(text: str) -> str:
    cleaned = text.strip().lower()
    for word in _STOP_WORDS:
        cleaned = cleaned.replace(word, "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _build(action: str, target: str, message: str) -> Dict[str, str]:
    return {"action": action, "target": target, "message": message, "type": "system"}


def route_command(text: str) -> Dict[str, str]:
    """Return a structured action dict for the given text command."""
    normalized = _normalize(text)

    if not normalized:
        return _build("noop", "", "Empty command.")

    # YouTube open variants
    if any(normalized.startswith(prefix) for prefix in ("open youtube", "launch youtube", "start youtube")) or "youtube.com" in normalized:
        return _build("open_url", "https://youtube.com", "Opening YouTube")

    # Chrome / browser launch
    if any(phrase in normalized for phrase in ("open chrome", "launch chrome", "start chrome")):
        return _build("open_app", "chrome", "Launching Chrome")

    # Open folder with dynamic path
    folder_match = re.match(r"^(open|launch|start)\s+folder\s+(.+)$", normalized)
    if folder_match:
        target = folder_match.group(2).strip().strip('"').strip("'")
        target = target or "~"
        return _build("open_folder", target, f"Opening folder {target}")

    # Generic open app
    generic_app = re.match(r"^(open|launch|start)\s+(.+)$", normalized)
    if generic_app:
        target = generic_app.group(2).strip()
        if target:
            return _build("open_app", target, f"Opening {target}")

    return _build("unknown", "", "Command not recognized. Try 'open youtube' or 'open folder <path>'.")
