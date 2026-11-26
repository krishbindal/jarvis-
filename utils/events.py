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

    def unsubscribe(self, event: str, handler: EventHandler) -> bool:
        """Remove a registered callback so closed widgets are never retained."""
        with self._lock:
            callbacks = self._handlers.get(event)
            if not callbacks:
                return False
            # Equality supports Qt/Python bound-method wrappers whose identity
            # need not be stable across attribute accesses.
            for index, callback in enumerate(callbacks):
                if callback == handler:
                    callbacks.pop(index)
                    if not callbacks:
                        self._handlers.pop(event, None)
                    return True
        return False

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
_event_bus_lock = threading.Lock()


def get_event_bus() -> EventBus:
    """Create the shared EventBus once even when multiple workers race."""
    global _event_bus
    if _event_bus is None:
        with _event_bus_lock:
            if _event_bus is None:
                _event_bus = EventBus()
    return _event_bus
