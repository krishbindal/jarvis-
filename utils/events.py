from __future__ import annotations

"""Thread-safe, lightweight event bus."""

import threading
from collections import defaultdict
from typing import Callable, DefaultDict, List, Optional

EventHandler = Callable[..., None]


from utils.logger import get_logger

logger = get_logger(__name__)

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
        
        logger.debug("[EVENT] Emitting: %s", event)
        for cb in callbacks:
            try:
                cb(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001
                logger.error("Handler for '%s' failed: %s", event, exc)

# Singleton Registry
_event_bus: Optional[EventBus] = None

def get_event_bus() -> EventBus:
    """Return the global EventBus singleton."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus
