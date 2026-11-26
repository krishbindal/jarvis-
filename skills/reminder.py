"""Bounded, uniquely identified reminder timers with reliable shutdown."""
from __future__ import annotations

import itertools
import re
import threading
from typing import Any, Dict

from utils.logger import get_logger

logger = get_logger(__name__)
SKILL_NAME = "reminder"
SKILL_DESCRIPTION = "Set reminders such as 'remind me in 5 minutes to check the build'."
SKILL_PATTERNS = [
    r"remind\s+me\s+in\s+(\d+)\s*(min|minute|minutes|sec|second|seconds|hour|hours)\s+(?:to\s+)?(.+)",
    r"set\s+(?:a\s+)?(?:timer|reminder)\s+(?:for\s+)?(\d+)\s*(min|minute|minutes|sec|second|seconds|hour|hours)\s+(?:to\s+)?(.+)",
    r"(?:timer|alarm)\s+(\d+)\s*(min|minute|minutes|sec|second|seconds|hour|hours)\s*(?:for\s+)?(.+)?",
]
_MAX_ACTIVE = 128
_MAX_DELAY_SECONDS = 7 * 24 * 3600
_LOCK = threading.RLock()
_IDS = itertools.count(1)
_active_reminders: dict[int, threading.Timer] = {}


def _parse_seconds(amount: int, unit: str) -> int:
    unit = unit.lower()
    if unit.startswith("min"):
        return amount * 60
    if unit.startswith("hour"):
        return amount * 3600
    return amount


def _fire_reminder(message: str, reminder_id: int) -> None:
    with _LOCK:
        if _active_reminders.pop(reminder_id, None) is None:
            return  # Cancelled by shutdown or removed.
    try:
        from voice.tts_engine import speak
        from utils.notifications import notify
        notify("Jarvis Reminder", message)
        speak(f"Reminder: {message}")
    except Exception as exc:
        logger.warning("[REMINDER] Failed to deliver notification (%s)", type(exc).__name__)


def cancel_all_reminders() -> int:
    """Cancel pending timers on app shutdown and return how many were cancelled."""
    with _LOCK:
        outstanding = list(_active_reminders.values())
        _active_reminders.clear()
    for timer in outstanding:
        timer.cancel()
    return len(outstanding)


def execute(target: str, extra: Dict[str, Any] = None) -> Dict[str, Any]:
    if not isinstance(target, str):
        return {"success": False, "status": "invalid_request", "message": "A text reminder is required."}

    match = next((m for pattern in SKILL_PATTERNS if (m := re.search(pattern, target, re.IGNORECASE))), None)
    if match is None:
        return {"success": False, "status": "error", "message": "Could not parse the reminder."}

    amount, unit = int(match.group(1)), match.group(2)
    message = (match.group(3) or "Time's up!").strip()
    seconds = _parse_seconds(amount, unit)
    if not (1 <= seconds <= _MAX_DELAY_SECONDS) or len(message) > 500:
        return {
            "success": False,
            "status": "invalid_reminder",
            "message": "Reminders must be 1 second to 7 days, with a message up to 500 characters.",
        }

    with _LOCK:
        if len(_active_reminders) >= _MAX_ACTIVE:
            return {"success": False, "status": "capacity_reached", "message": "Too many active reminders."}
        reminder_id = next(_IDS)
        timer = threading.Timer(seconds, _fire_reminder, args=(message, reminder_id))
        timer.daemon = True
        _active_reminders[reminder_id] = timer
        try:
            timer.start()
        except RuntimeError:
            _active_reminders.pop(reminder_id, None)
            return {"success": False, "status": "error", "message": "Could not start the reminder timer."}

    logger.info("[REMINDER] Scheduled id=%d seconds=%d", reminder_id, seconds)
    return {
        "success": True,
        "status": "scheduled",
        "message": f"Reminder {reminder_id} scheduled for {amount} {unit}. It has not fired yet.",
        "output": f"reminder_{reminder_id}",
    }
