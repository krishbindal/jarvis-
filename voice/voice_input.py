from __future__ import annotations

"""Voice input utilities for Jarvis."""

from typing import Optional

from utils.logger import get_logger

logger = get_logger(__name__)

try:
    import speech_recognition as sr
except Exception as exc:  # noqa: BLE001
    sr = None
    logger.error("speech_recognition is not available: %s", exc)


def listen_for_command(
    timeout: float = 5.0,
    phrase_time_limit: float = 10.0,
    wake_word: Optional[str] = "jarvis",
    require_wake_word: bool = False,
) -> str:
    """
    Capture microphone input and convert speech to text.

    Returns an empty string when no speech is detected or recognition fails.
    """

    if sr is None:
        logger.error("Voice input unavailable: install the speech_recognition package.")
        return ""

    recognizer = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            logger.info("Listening for a voice command...")
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
    except sr.WaitTimeoutError:
        logger.info("Voice input timed out waiting for speech.")
        return ""
    except Exception as exc:  # noqa: BLE001
        logger.error("Microphone capture failed: %s", exc)
        return ""

    try:
        transcript = recognizer.recognize_google(audio)
    except sr.UnknownValueError:
        logger.info("Could not understand the audio.")
        return ""
    except sr.RequestError as exc:  # noqa: B904
        logger.error("Speech recognition request failed: %s", exc)
        return ""
    except Exception as exc:  # noqa: BLE001
        logger.error("Unexpected voice transcription error: %s", exc)
        return ""

    cleaned = transcript.strip()
    if not cleaned:
        logger.info("Voice transcription returned empty text.")
        return ""

    if wake_word:
        lower = cleaned.lower()
        trigger = wake_word.lower()
        if trigger in lower:
            idx = lower.find(trigger)
            cleaned = (cleaned[:idx] + cleaned[idx + len(trigger) :]).strip(" ,")
        elif require_wake_word:
            logger.info("Wake word '%s' not detected; ignoring voice input.", wake_word)
            return ""

    logger.info("Captured voice command: %s", cleaned)
    return cleaned
