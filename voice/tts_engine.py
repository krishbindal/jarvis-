from __future__ import annotations

"""Lightweight text-to-speech stub to avoid blocking dependencies."""

from utils.logger import get_logger

logger = get_logger(__name__)


def speak(text: str) -> None:
    """Speak or log the text. Falls back to logging when no TTS backend exists."""
    if not text:
        return
    try:
        import pyttsx3  # type: ignore

        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
    except Exception:
        logger.info("[VOICE][TTS] %s", text)
