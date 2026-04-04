from __future__ import annotations

"""Thread-safe, lightweight event bus."""

import threading
from collections import defaultdict
from typing import Callable, DefaultDict, List

EventHandler = Callable[..., None]


class EventBus:
    """Lightweight event bus for decoupled communication."""

    def __init__(self) -> None:
        self._handlers: DefaultDict[str, List[EventHandler]] = defaultdict(list)
        self._lock = threading.Lock()

    def subscribe(self, event: str, handler: EventHandler) -> None:
        """Register a handler for the given event."""
        with self._lock:
            self._handlers[event].append(handler)

    def emit(self, event: str, *args, **kwargs) -> None:
        """Emit an event to all subscribers with debug logging."""
        with self._lock:
            callbacks = list(self._handlers.get(event, ()))
        print(f"[EVENT] Emitting: {event}")
        for cb in callbacks:
            try:
                cb(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001
                print(f"Handler for '{event}' failed: {exc}")
