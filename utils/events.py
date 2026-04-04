from __future__ import annotations

import threading
from collections import defaultdict
from typing import Callable, DefaultDict, Dict, List

EventHandler = Callable[..., None]


class EventBus:
    """Lightweight event bus for decoupled communication."""

    def __init__(self) -> None:
        self._handlers: DefaultDict[str, List[EventHandler]] = defaultdict(list)
        self._lock = threading.Lock()

    def subscribe(self, event: str, handler: EventHandler) -> None:
        with self._lock:
            self._handlers[event].append(handler)

    def emit(self, event: str, *args, **kwargs) -> None:
        with self._lock:
            callbacks = list(self._handlers.get(event, ()))
        for cb in callbacks:
            try:
                cb(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001
                print(f"Handler for '{event}' failed: {exc}")
