from __future__ import annotations

"""Simple rule-based command router for Phase 2."""

from typing import Dict


def route_command(text: str) -> Dict[str, str]:
    """Return a structured action dict for the given text command."""
    normalized = text.strip().lower()

    if not normalized:
        return {"action": "noop", "target": "", "message": "Empty command."}

    if "youtube" in normalized:
        return {"action": "open_url", "target": "https://youtube.com", "message": "Opening YouTube"}

    if "open chrome" in normalized or "launch chrome" in normalized:
        return {"action": "open_app", "target": "chrome", "message": "Launching Chrome"}

    if normalized.startswith("open folder"):
        target = normalized.replace("open folder", "", 1).strip() or "~"
        return {"action": "open_folder", "target": target, "message": f"Opening folder {target}"}

    if normalized.startswith("open "):
        target = normalized.replace("open", "", 1).strip()
        if target:
            return {"action": "open_app", "target": target, "message": f"Opening {target}"}

    return {"action": "unknown", "target": "", "message": "Command not recognized yet."}
