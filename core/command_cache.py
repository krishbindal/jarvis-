"""
Command Cache — LRU cache for frequently repeated commands.

Phase 11: Performance optimization
- Avoids reparsing identical inputs
- Avoids repeated AI calls for the same unknown command
- Thread-safe with TTL expiry
"""

from __future__ import annotations

import threading
import time
from collections import OrderedDict
from typing import Any, Dict, Optional


class CommandCache:
    """Thread-safe LRU cache with TTL for parsed commands."""

    def __init__(self, max_size: int = 128, ttl_seconds: float = 300.0):
        self._lock = threading.Lock()
        self._cache: OrderedDict[str, _CacheEntry] = OrderedDict()
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve a cached parse result, or None if miss/expired."""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._misses += 1
                return None
            if time.monotonic() - entry.timestamp > self._ttl:
                # Expired
                del self._cache[key]
                self._misses += 1
                return None
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            self._hits += 1
            return entry.value

    def put(self, key: str, value: Dict[str, Any]) -> None:
        """Store a parse result."""
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                self._cache[key] = _CacheEntry(value)
            else:
                if len(self._cache) >= self._max_size:
                    self._cache.popitem(last=False)
                self._cache[key] = _CacheEntry(value)

    def invalidate(self, key: str) -> None:
        """Remove a specific key."""
        with self._lock:
            self._cache.pop(key, None)

    def clear(self) -> None:
        """Flush the entire cache."""
        with self._lock:
            self._cache.clear()

    @property
    def stats(self) -> Dict[str, int]:
        with self._lock:
            return {
                "size": len(self._cache),
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(self._hits / max(1, self._hits + self._misses) * 100, 1),
            }


class _CacheEntry:
    __slots__ = ("value", "timestamp")

    def __init__(self, value: Dict[str, Any]):
        self.value = value
        self.timestamp = time.monotonic()


# Global singleton
route_cache = CommandCache(max_size=256, ttl_seconds=600.0)
