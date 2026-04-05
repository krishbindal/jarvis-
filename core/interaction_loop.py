from __future__ import annotations

"""Real-time interaction coordinator for speech, UI, and streaming updates."""

import random
import threading
from typing import Optional

from brain.streaming_llm import stream_response
from utils.logger import get_logger
from voice.tts_engine import speak

logger = get_logger(__name__)


ACKS = [
    "Yes, on it.",
    "Got it.",
    "Right away.",
    "Understood.",
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


class InteractionLoop:
    """Drives micro-interactions to avoid dead air across the stack."""

    def __init__(self, event_bus) -> None:
        self._events = event_bus
        self._stop_stream = threading.Event()
        self._stream_thread: Optional[threading.Thread] = None

    def reset(self) -> None:
        self._stop_stream.clear()

    def stop(self) -> None:
        self._stop_stream.set()

    def immediate_ack(self, command: str) -> None:
        """Speak and surface a quick acknowledgment."""
        ack = random.choice(ACKS)
        if self._events:
            self._events.emit("overlay_state", {"state": "listening", "text": command[:40]})
            self._events.emit("cinematic_log", {"text": f"[USER] {command}"})
        speak(ack)

    def narrate_action(self, action: str, target: str) -> None:
        """Provide a short in-flight narration."""
        verb = ACTION_VERBS.get(action, "Working on")
        snippet = target[:60] if target else ""
        line = f"{verb} {snippet}".strip()
        if self._events:
            self._events.emit("command_progress", {"stage": "action", "text": line})
            self._events.emit("overlay_state", {"state": "thinking", "text": line[:40]})
        if line:
            speak(line)

    def finish(self, message: str) -> None:
        """Stop streaming and deliver the closing line."""
        self.stop()
        if self._stream_thread and self._stream_thread.is_alive():
            self._stream_thread.join(timeout=0.2)
        final = message or "Done."
        if self._events:
            self._events.emit("command_progress", {"stage": "done", "text": final})
            self._events.emit("overlay_state", {"state": "idle", "text": final[:40]})
        speak(final)

    def stream_thinking(self, command: str) -> None:
        """Start a background streamer that narrates thinking tokens."""
        self._stop_stream.clear()
        system_prompt = (
            "You are Jarvis narrating your work. Reply in very short, confident bullet fragments "
            "that describe what you are doing step by step. Keep it concise and cinematic."
        )
        user_prompt = f"Narrate how you will handle: {command}"

        def _runner() -> None:
            for token in stream_response(user_prompt, system_prompt=system_prompt):
                if self._stop_stream.is_set():
                    break
                if self._events:
                    self._events.emit("stream_output", {"token": token})
            if self._events and not self._stop_stream.is_set():
                self._events.emit("stream_output", {"token": "\n", "reset": False})

        self._stream_thread = threading.Thread(target=_runner, name="jarvis-stream", daemon=True)
        self._stream_thread.start()
