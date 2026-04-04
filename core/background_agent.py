from __future__ import annotations

"""Background agent to watch patterns and emit proactive suggestions."""

import threading
import time
from typing import Any, Dict

import config
from memory.memory_store import get_frequent_commands
from utils.logger import get_logger

logger = get_logger(__name__)


class BackgroundAgent:
    def __init__(self, event_bus) -> None:
        self._event_bus = event_bus
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return

        def _run() -> None:
            while not self._stop.is_set():
                try:
                    suggestions = self._gather_signals()
                    if suggestions:
                        self._event_bus.emit("background_suggestion", {"suggestions": suggestions})
                except Exception as exc:  # noqa: BLE001
                    logger.error("[BG] Background loop error: %s", exc)
                self._stop.wait(config.BACKGROUND_POLL_S)

        self._thread = threading.Thread(target=_run, name="background-agent", daemon=True)
        self._thread.start()
        logger.info("[BG] Background agent started")

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.2)

    def _gather_signals(self) -> list[Dict[str, Any]]:
        frequent = get_frequent_commands(limit=config.BACKGROUND_SUGGESTION_LIMIT)
        suggestions = []
        for item in frequent:
            action = item.get("action", "")
            count = item.get("count", 0)
            if action:
                suggestions.append({"action": action, "count": count, "message": f"You run '{action}' often. Want to make it a macro?"})
        return suggestions
