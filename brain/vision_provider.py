"""
JARVIS-X Phase 16: Multimodal Vision Provider (The "Eyes")

Background service that periodically captures the screen and uses
Gemini 1.5 Flash (Free Tier) to summarize the user's current activity.
This context is injected into AI prompts for proactive intelligence.
"""

from __future__ import annotations

import base64
import io
import os
import threading
import time
from typing import Optional, Dict, Any

from google import genai
from google.genai import types
from PIL import Image

from config import GEMINI_API_KEY
from utils.logger import get_logger

logger = get_logger(__name__)

# How often to scan (seconds)
DEFAULT_SCAN_INTERVAL = 30
VISION_MODEL = "gemini-2.0-flash"

VISION_PROMPT = """You are observing a user's desktop screen. In 2-3 sentences, describe:
1. What application is in the foreground (e.g., VS Code, Chrome, Slack, Terminal).
2. What the user appears to be working on (e.g., coding in Python, browsing documentation, chatting).
3. Any notable details (error messages, file names, URLs visible).

Be concise and factual. Do NOT invent information you can't see."""


class VisionProvider:
    """Background screen observer using Gemini Vision (Free Tier)."""

    def __init__(self, interval: int = DEFAULT_SCAN_INTERVAL) -> None:
        self._interval = interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._last_summary: str = "No visual context yet."
        self._last_capture_time: float = 0.0
        self._consecutive_errors = 0

    @property
    def last_summary(self) -> str:
        with self._lock:
            return self._last_summary

    @property
    def is_active(self) -> bool:
        return self._running

    def start(self) -> None:
        """Start the background vision loop."""
        if not GEMINI_API_KEY:
            logger.warning("[VISION] No GEMINI_API_KEY set — Vision provider disabled.")
            return

        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._loop, name="vision-provider", daemon=True)
        self._thread.start()
        logger.info("[VISION] Background vision provider started (interval=%ds)", self._interval)

    def stop(self) -> None:
        """Stop the background vision loop."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        logger.info("[VISION] Vision provider stopped.")

    def capture_now(self) -> str:
        """Force an immediate screen capture and analysis. Returns the summary."""
        return self._capture_and_analyze()

    def _loop(self) -> None:
        """Main background loop."""
        # Initial delay to let the system settle
        time.sleep(5)
        from utils.resource_manager import get_resource_manager
        rm = get_resource_manager()

        while self._running:
            try:
                self._capture_and_analyze()
                self._consecutive_errors = 0
            except Exception as e:
                self._consecutive_errors += 1
                logger.error("[VISION] Capture failed (attempt %d): %s", self._consecutive_errors, e)
                if self._consecutive_errors >= 5:
                    logger.error("[VISION] Too many consecutive failures. Pausing for 5 minutes.")
                    time.sleep(300)
                    self._consecutive_errors = 0

            # Scale interval based on system load
            throttle = rm.get_throttle_level()
            effective_interval = self._interval * throttle
            if throttle > 1.0:
                logger.debug(f"[VISION] Throttling interval to {effective_interval}s due to system load.")
            
            time.sleep(effective_interval)

    def _capture_and_analyze(self) -> str:
        """Take a screenshot and send it to Gemini Flash for analysis."""
        try:
            import mss

            with mss.mss() as sct:
                # Phase 29: Multi-monitor — capture ALL monitors
                if len(sct.monitors) > 2:
                    # monitors[0] is the virtual screen (all combined)
                    screenshot = sct.grab(sct.monitors[0])
                    logger.debug("[VISION] Captured %d monitors (combined)", len(sct.monitors) - 1)
                else:
                    screenshot = sct.grab(sct.monitors[1])

            # Convert to PIL Image and resize for efficiency
            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
            # Downscale to ~720p to save bandwidth (free tier)
            max_width = 1280
            if img.width > max_width:
                ratio = max_width / img.width
                img = img.resize((max_width, int(img.height * ratio)), Image.LANCZOS)

            # Save latest capture for reference
            os.makedirs("assets/memory", exist_ok=True)
            img.save("assets/memory/last_screen.png", "PNG")

            # Encode to bytes for Gemini
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=60)
            buf.seek(0)

            # Send to Gemini Vision
            client = genai.Client(api_key=GEMINI_API_KEY)
            
            response = client.models.generate_content(
                model=VISION_MODEL,
                contents=[
                    VISION_PROMPT,
                    types.Part.from_bytes(data=buf.read(), mime_type="image/jpeg")
                ]
            )

            summary = response.text.strip()
            with self._lock:
                self._last_summary = summary
                self._last_capture_time = time.time()

            logger.info("[VISION] Screen analyzed: %s", summary[:80])
            return summary

        except Exception as e:
            logger.error("[VISION] Analysis failed: %s", e)
            return self._last_summary


# Global singleton
_provider: Optional[VisionProvider] = None


def get_vision_provider() -> VisionProvider:
    """Return the global VisionProvider singleton."""
    global _provider
    if _provider is None:
        _provider = VisionProvider()
    return _provider


def get_visual_context() -> str:
    """Convenience function to get the latest visual context summary."""
    provider = get_vision_provider()
    return provider.last_summary
