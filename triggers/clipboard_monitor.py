"""
JARVIS-X Phase 22: Clipboard Intelligence

Monitors the clipboard for changes and offers contextual actions.
- URL detected → offer to open in browser
- Code detected → offer to explain
- Long text → offer to summarize
"""

from __future__ import annotations

import re
import threading
import time
from typing import Optional

from utils.logger import get_logger

logger = get_logger(__name__)

# Patterns
URL_PATTERN = re.compile(r'https?://\S+', re.IGNORECASE)
CODE_INDICATORS = ['def ', 'function ', 'class ', 'import ', 'const ', 'let ', 'var ', '#include', 'public static']


class ClipboardMonitor:
    """Background monitor for clipboard changes."""

    def __init__(self, event_bus=None) -> None:
        self._events = event_bus
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_content = ""

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, name="clipboard-monitor", daemon=True)
        self._thread.start()
        logger.info("[CLIPBOARD] Monitor started.")

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1)
        logger.info("[CLIPBOARD] Monitor stopped.")

    def _loop(self) -> None:
        """Poll clipboard every 2 seconds for changes."""
        time.sleep(5)  # Initial delay
        while self._running:
            try:
                import win32clipboard
                win32clipboard.OpenClipboard()
                try:
                    content = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
                except Exception:
                    content = None
                finally:
                    win32clipboard.CloseClipboard()

                if content and content != self._last_content:
                    self._last_content = content
                    self._analyze(content)

            except Exception as e:
                logger.debug("[CLIPBOARD] Poll error: %s", e)

            time.sleep(2)

    def _analyze(self, content: str) -> None:
        """Analyze clipboard content and emit appropriate events."""
        content_stripped = content.strip()

        if not content_stripped or len(content_stripped) < 5:
            return

        # Check for URLs
        if URL_PATTERN.match(content_stripped):
            logger.info("[CLIPBOARD] URL detected: %s", content_stripped[:60])
            if self._events:
                self._events.emit("clipboard_url", {"url": content_stripped})
                from utils.notifications import notify
                notify("📋 URL Copied", f"Jarvis detected a URL: {content_stripped[:50]}...")
            return

        # Check for code
        if any(indicator in content_stripped for indicator in CODE_INDICATORS):
            logger.info("[CLIPBOARD] Code snippet detected (%d chars)", len(content_stripped))
            if self._events:
                self._events.emit("clipboard_code", {"code": content_stripped[:500]})
                from utils.notifications import notify
                notify("📋 Code Copied", "Jarvis can explain this code. Just ask!")
            return

        # Long text → offer summary
        if len(content_stripped) > 200:
            logger.info("[CLIPBOARD] Long text detected (%d chars)", len(content_stripped))
            if self._events:
                self._events.emit("clipboard_text", {"text": content_stripped[:500]})
            return
