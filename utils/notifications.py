"""
JARVIS-X Phase 23: Smart Desktop Notifications

Cross-platform (Windows-focused) notification system using winotify.
Provides native Windows 10/11 toast notifications.
"""

from __future__ import annotations

import threading
from utils.logger import get_logger

logger = get_logger(__name__)


def notify(title: str, message: str, icon: str = None, duration: str = "short") -> None:
    """Send a Windows toast notification (non-blocking)."""

    def _send():
        try:
            from winotify import Notification, audio

            toast = Notification(
                app_id="JARVIS-X Copilot",
                title=title,
                msg=message,
                duration=duration,
            )

            if icon:
                toast.set_audio(audio.Default, loop=False)

            toast.show()
            logger.info("[NOTIFY] Sent: %s — %s", title, message[:50])

        except ImportError:
            # Fallback to basic win10toast or just log
            logger.warning("[NOTIFY] winotify not installed. Logging notification instead.")
            logger.info("[NOTIFY] %s: %s", title, message)
        except Exception as e:
            logger.error("[NOTIFY] Failed to send notification: %s", e)

    threading.Thread(target=_send, daemon=True).start()
