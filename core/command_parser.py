"""
Command Parser — NLP pre-processing, multi-step splitting, and context awareness.

Phase 5: Multi-step command support
Phase 6: Context awareness (session memory)
Phase 9: Command normalization
"""

from __future__ import annotations

import re
import threading
from collections import deque
from typing import Dict, List, Optional


# ─────────────────────────────────────────────────────────
# NLP Normalization (Phase 9)
# ─────────────────────────────────────────────────────────

_STOP_WORDS = ("please", "jarvis", "hey jarvis", "okay jarvis", "ok jarvis")

_FILLER_PHRASES = (
    "can you ", "could you ", "would you ", "will you ",
    "i want you to ", "i need you to ", "i'd like you to ",
    "please ", "now ", "just ", "go ahead and ",
    "for me ", "kindly ", "try to ", "i want to ",
    "let's ", "let me ", "help me ",
)

# Conjunctions that split multi-step commands
_STEP_SPLITTERS = (
    " and then ",
    " then ",
    " and also ",
    " also ",
    " and ",
    " after that ",
    " next ",
)


def normalize(text: str) -> str:
    """Normalize a raw command string: lowercase, strip fillers, collapse whitespace."""
    cleaned = text.strip().lower()

    # Remove stop words
    for word in _STOP_WORDS:
        cleaned = cleaned.replace(word, "")

    # Strip leading filler phrases (can chain: "can you please just open...")
    changed = True
    while changed:
        changed = False
        cleaned = re.sub(r"\s+", " ", cleaned).strip()  # collapse between iterations
        for filler in _FILLER_PHRASES:
            if cleaned.startswith(filler):
                cleaned = cleaned[len(filler):]
                changed = True
                break

    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def split_multi_step(text: str) -> List[str]:
    """
    Phase 5: Split compound commands on natural language conjunctions.

    "open chrome and search youtube" → ["open chrome", "search youtube"]
    "open youtube then play music"   → ["open youtube", "play music"]

    Single commands pass through unchanged as a list of one.
    """
    normalized = normalize(text)

    # Try each splitter (longest first for greedy match)
    for splitter in _STEP_SPLITTERS:
        if splitter in normalized:
            parts = normalized.split(splitter)
            # Each part gets re-normalized to strip any stray fillers
            steps = [normalize(p) for p in parts if normalize(p)]
            if len(steps) >= 2:
                return steps

    return [normalized] if normalized else []


# ─────────────────────────────────────────────────────────
# Session Context (Phase 6)
# ─────────────────────────────────────────────────────────

class SessionContext:
    """
    Tracks recent command context within a session for intelligent continuity.

    Examples of context-aware behavior:
        User: "open chrome"       → last_app = "chrome"
        User: "open youtube"      → uses chrome context → opens youtube IN chrome
        User: "go to github.com"  → uses chrome context → opens github IN chrome
    """

    def __init__(self, max_history: int = 20):
        self._lock = threading.Lock()
        self._history: deque = deque(maxlen=max_history)
        self._last_app: Optional[str] = None
        self._last_action: Optional[str] = None
        self._last_target: Optional[str] = None

    def record(self, action: str, target: str, app: Optional[str] = None) -> None:
        """Record an executed command for context tracking."""
        with self._lock:
            self._history.append({
                "action": action,
                "target": target,
                "app": app,
            })
            if app:
                self._last_app = app
            self._last_action = action
            self._last_target = target

    @property
    def last_app(self) -> Optional[str]:
        with self._lock:
            return self._last_app

    @property
    def last_action(self) -> Optional[str]:
        with self._lock:
            return self._last_action

    @property
    def last_target(self) -> Optional[str]:
        with self._lock:
            return self._last_target

    @property
    def history(self) -> List[Dict]:
        with self._lock:
            return list(self._history)

    def get_context_app(self) -> Optional[str]:
        """
        Get the most recently used app if it was a browser or editor,
        so follow-up commands can reuse it.
        """
        with self._lock:
            if self._last_app and self._last_app in (
                "chrome", "msedge", "firefox", "brave", "code", "explorer"
            ):
                return self._last_app
        return None

    def clear(self) -> None:
        with self._lock:
            self._history.clear()
            self._last_app = None
            self._last_action = None
            self._last_target = None


# Global session context (lives for the runtime of Jarvis)
session = SessionContext()
