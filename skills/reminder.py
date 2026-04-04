"""
JARVIS-X Phase 28: Scheduled Reminders

Skill: Set timers and reminders that fire TTS notifications.
"""

import threading
import re
from typing import Any, Dict, Optional
from utils.logger import get_logger

logger = get_logger(__name__)

SKILL_NAME = "reminder"
SKILL_DESCRIPTION = "Set timed reminders — 'remind me in 5 minutes to check the build'"
SKILL_PATTERNS = [
    r"remind\s+me\s+in\s+(\d+)\s*(min|minute|minutes|sec|second|seconds|hour|hours)\s+(?:to\s+)?(.+)",
    r"set\s+(?:a\s+)?(?:timer|reminder)\s+(?:for\s+)?(\d+)\s*(min|minute|minutes|sec|second|seconds|hour|hours)\s+(?:to\s+)?(.+)",
    r"(?:timer|alarm)\s+(\d+)\s*(min|minute|minutes|sec|second|seconds|hour|hours)\s*(?:for\s+)?(.+)?",
]

_active_reminders: list = []


def _parse_seconds(amount: int, unit: str) -> int:
    """Convert amount + unit to seconds."""
    unit = unit.lower()
    if unit.startswith("min"):
        return amount * 60
    elif unit.startswith("hour"):
        return amount * 3600
    else:
        return amount


def _fire_reminder(message: str, reminder_id: int):
    """Called when the timer expires."""
    try:
        from voice.tts_engine import speak
        from utils.notifications import notify
        logger.info("[REMINDER] Firing: %s", message)
        notify("⏰ Jarvis Reminder", message)
        speak(f"Reminder: {message}")
    except Exception as e:
        logger.error("[REMINDER] Failed to fire: %s", e)
    finally:
        # Clean up
        _active_reminders[:] = [r for r in _active_reminders if r["id"] != reminder_id]


def execute(target: str, extra: Dict[str, Any] = None) -> Dict[str, Any]:
    """Set a reminder."""
    extra = extra or {}

    # Try to parse from target text
    for pattern in SKILL_PATTERNS:
        match = re.search(pattern, target, re.IGNORECASE)
        if match:
            amount = int(match.group(1))
            unit = match.group(2)
            message = match.group(3) or "Time's up!"
            break
    else:
        return {"success": False, "status": "error", "message": "Could not parse reminder."}

    seconds = _parse_seconds(amount, unit)
    reminder_id = len(_active_reminders) + 1

    timer = threading.Timer(seconds, _fire_reminder, args=[message.strip(), reminder_id])
    timer.daemon = True
    timer.start()

    _active_reminders.append({
        "id": reminder_id,
        "message": message.strip(),
        "seconds": seconds,
        "timer": timer,
    })

    friendly = f"{amount} {unit}"
    logger.info("[REMINDER] Set: '%s' in %s (%ds)", message, friendly, seconds)

    return {
        "success": True,
        "status": "success",
        "message": f"Reminder set for {friendly}: {message.strip()}",
        "output": f"reminder_{reminder_id}",
    }
