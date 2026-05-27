from __future__ import annotations

"""Real-time interaction coordinator for speech, UI, and streaming updates."""

import random
import threading
import time
from typing import Optional

from utils.logger import get_logger
from voice.tts_engine import speak

logger = get_logger(__name__)


ACKS = [
    "Sure thing.",
    "On it now.",
    "Got it.",
    "I'll take care of it.",
    "Working on that.",
    "You got it.",
    "Absolutely.",
]

ACTION_VERBS = {
    "open_app": "Launching",
    "open_url": "Opening",
    "open_dynamic": "Opening",
    "open_folder": "Opening folder",
    "quick_search": "Searching",
    "download_file": "Downloading",
    "download_video": "Fetching video",
    "convert_to_mp3": "Converting",
    "convert_to_pdf": "Converting",
    "kill_process": "Stopping",
    "type_text": "Typing",
    "press_key": "Pressing",
    "click": "Clicking",
    "read_screen": "Scanning",
    "get_active_app": "Checking",
}

# Actions that typically complete in under a second — skip ack + narration
QUICK_ACTIONS = {
    "open_app", "open_url", "open_dynamic", "open_folder",
    "kill_process", "media_control", "power_state",
    "press_key", "click", "type_text",
}


class InteractionLoop:
    """Drives micro-interactions to avoid dead air across the stack."""

    def __init__(self, event_bus) -> None:
        self._events = event_bus
        self._stop_stream = threading.Event()
        self._stream_thread: Optional[threading.Thread] = None
        self._finished = False  # Guard against double-finish
        self._quick = False     # Whether this is a fast/deterministic command
        self._ack_spoken = False
        self._ack_time: float = 0.0

    def reset(self) -> None:
        self._stop_stream.clear()
        self._finished = False
        self._quick = False
        self._ack_spoken = False
        self._ack_time = 0.0

    def set_quick(self, quick: bool = True) -> None:
        """Mark this command cycle as quick — suppresses ack and narration."""
        self._quick = quick

    def stop(self) -> None:
        self._stop_stream.set()

    def immediate_ack(self, command: str) -> None:
        """Speak and surface a quick acknowledgment (skipped for quick commands)."""
        if self._events:
            self._events.emit("overlay_state", {"state": "listening", "text": command[:40]})
            self._events.emit("cinematic_log", {"text": f"[USER] {command}"})

        if self._quick:
            # For quick commands, log in UI but don't speak — the result will speak instead
            return

        ack = random.choice(ACKS)
        self._ack_spoken = True
        self._ack_time = time.monotonic()
        
        def _delayed_ack():
            time.sleep(0.4)
            if not self._finished:
                speak(ack)
                
        threading.Thread(target=_delayed_ack, daemon=True).start()

    def narrate_action(self, action: str, target: str) -> None:
        """Provide a short in-flight narration (skipped for quick commands)."""
        verb = ACTION_VERBS.get(action, "Working on")
        snippet = target[:60] if target else ""
        line = f"{verb} {snippet}".strip()

        if self._events:
            self._events.emit("command_progress", {"stage": "action", "text": line})
            self._events.emit("overlay_state", {"state": "thinking", "text": line[:40]})

        if self._quick:
            # For quick commands, show in UI but don't speak — result will speak instead
            return

        if line:
            speak(line)

    def finish(self, message: str, emotion: str = "normal") -> None:
        """Stop streaming and deliver the closing line."""
        # Guard: only deliver the closing line once per command cycle
        if self._finished:
            return
        self._finished = True

        self.stop()
        if self._stream_thread and self._stream_thread.is_alive():
            self._stream_thread.join(timeout=0.2)
        final = message or "Done."
        if self._events:
            self._events.emit("command_progress", {"stage": "done", "text": final})
            self._events.emit("overlay_state", {"state": "idle", "text": final[:40]})
        speak(final, emotion=emotion)
