"""
JARVIS-X Phase 22: Oracle Clipboard Intelligence

Monitors the clipboard for changes and performs proactive background audits.
- URL detected → fetch summary
- Code detected → perform bug audit
- Long text → summarize
"""

from __future__ import annotations

import re
import threading
import time
import requests
from typing import Optional

from utils.logger import get_logger
from utils.connectivity import is_online
from brain.ai_engine import query_ai

logger = get_logger(__name__)

# Patterns
URL_PATTERN = re.compile(r'https?://\S+', re.IGNORECASE)
CODE_INDICATORS = ['def ', 'function ', 'class ', 'import ', 'const ', 'let ', 'var ', '#include', 'public static']


class ClipboardMonitor:
    """Background monitor for clipboard changes with Oracle analysis."""

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
        logger.info("[CLIPBOARD] Oracle Monitor started.")

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1)
        logger.info("[CLIPBOARD] Oracle Monitor stopped.")

    def _loop(self) -> None:
        """Poll clipboard for changes."""
        time.sleep(2)
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

            time.sleep(1.5)

    def _analyze(self, content: str) -> None:
        """Categorize and trigger background oracle audit."""
        content_stripped = content.strip()
        if not content_stripped or len(content_stripped) < 5:
            return

        # 1. Immediate Notification (Existing)
        if URL_PATTERN.match(content_stripped):
            self._events.emit("clipboard_url", {"url": content_stripped})
            threading.Thread(target=self._oracle_link, args=(content_stripped,), daemon=True).start()
        elif any(indicator in content_stripped for indicator in CODE_INDICATORS):
            self._events.emit("clipboard_code", {"code": content_stripped})
            threading.Thread(target=self._oracle_code, args=(content_stripped,), daemon=True).start()
        elif len(content_stripped) > 300:
            self._events.emit("clipboard_text", {"text": content_stripped})
            threading.Thread(target=self._oracle_text, args=(content_stripped,), daemon=True).start()
            
        # Phase 22: Universal Memory Storage (Proactive)
        if len(content_stripped) > 500:
             logger.info("[CLIPBOARD] Long content detected. Proactively saving to system memory.")
             from memory.memory_store import get_memory_store
             mem = get_memory_store()
             mem.add_memory(f"User copied long text: {content_stripped[:200]}...", "clipboard_audit")
             self._events.emit("tts_request", "Sir, I've noted that long snippet in your system memory for later reference.")

    def _oracle_link(self, url: str) -> None:
        """Oracle Audit: Summarize URL metadata."""
        if not is_online():
            return
        try:
            logger.info(f"[ORACLE] Auditing link: {url[:50]}...")
            # Use AI to summarize what this link might be based on the URL itself
            # or do a HEAD request to get title if possible
            summary = query_ai(f"I just copied this link: {url}. Briefly tell me what it is in 5 words.", "You are Jarvis' Oracle.")
            if "unavailable" not in summary.lower():
                logger.info(f"[ORACLE] Link identity: {summary}")
                self._events.emit("tts_request", f"Sir, that link appears to be {summary}.")
        except Exception as e:
            logger.debug(f"Oracle link audit failed: {e}")

    def _oracle_code(self, code: str) -> None:
        """Oracle Audit: Bug check and explanation."""
        logger.info(f"[ORACLE] Auditing code snippet ({len(code)} chars)...")
        prompt = (
            f"Audit this code snippet and respond ONLY if you find a CRITICAL bug or a major optimization. "
            f"If it looks fine, say 'CLEAR'. Otherwise, 10 words maximum on the fix.\n\nCODE:\n{code[:1000]}"
        )
        audit = query_ai(prompt, "You are Jarvis' Oracle Code Auditor.")
        
        if audit and "CLEAR" not in audit.upper() and "unavailable" not in audit.lower():
            logger.warning(f"[ORACLE] Code Warning: {audit}")
            self._events.emit("tts_request", f"Sir, a quick audit of that code suggests: {audit}")

    def _oracle_text(self, text: str) -> None:
        """Oracle Audit: Long text summary."""
        logger.info(f"[ORACLE] Summarizing long text...")
        summary = query_ai(f"Summarize this into one short sentence:\n{text[:1000]}", "You are Jarvis' Summarizer.")
        if summary and "unavailable" not in summary.lower():
            logger.info(f"[ORACLE] Summary: {summary}")
            # Don't speak summary automatically, just log it
