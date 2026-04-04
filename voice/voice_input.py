from __future__ import annotations

"""Offline voice input using Vosk and sounddevice."""

import json
import queue
import time
from pathlib import Path
from typing import Optional

import sounddevice as sd

import config
from utils.logger import get_logger

logger = get_logger(__name__)

try:
    from vosk import KaldiRecognizer, Model
except Exception as exc:  # noqa: BLE001
    KaldiRecognizer = None
    Model = None
    logger.error("Vosk is not available: %s", exc)

_MODEL: Optional[Model] = None


def _load_model(path: str | Path) -> Optional[Model]:
    """Load and cache the Vosk model."""
    global _MODEL
    if _MODEL is not None:
        return _MODEL
    if Model is None:
        logger.error("Vosk dependency missing; install the 'vosk' package.")
        return None

    model_path = Path(path)
    if not model_path.exists():
        logger.error("Voice model not found at %s", model_path)
        return None

    try:
        _MODEL = Model(str(model_path))
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to load Vosk model: %s", exc)
        return None
    return _MODEL


def listen_for_command(
    timeout: float = 6.0,
    phrase_time_limit: float = 10.0,
    sample_rate: int = 16_000,
) -> Optional[str]:
    """
    Capture microphone input and convert speech to text using Vosk.

    Returns None when no valid speech is detected or recognition fails.
    """

    model = _load_model(config.VOICE_MODEL_PATH)
    if model is None or KaldiRecognizer is None:
        return None

    audio_queue: "queue.Queue[bytes]" = queue.Queue()

    def _callback(indata, frames, time_info, status) -> None:  # type: ignore[override]
        if status:
            logger.debug("Audio status: %s", status)
        audio_queue.put(bytes(indata))

    recognizer = KaldiRecognizer(model, sample_rate)
    recognizer.SetWords(True)

    speech_started_at: Optional[float] = None
    listen_started_at = time.monotonic()

    try:
        with sd.RawInputStream(
            samplerate=sample_rate,
            blocksize=8000,
            dtype="int16",
            channels=1,
            callback=_callback,
        ):
            while True:
                wait_timeout = timeout if speech_started_at is None else 1.0
                try:
                    data = audio_queue.get(timeout=wait_timeout)
                except queue.Empty:
                    logger.info("No speech detected within timeout window.")
                    return None

                if recognizer.AcceptWaveform(data):
                    result = json.loads(recognizer.Result() or "{}")
                    text = (result.get("text") or "").strip()
                    if text:
                        logger.info("Captured voice command: %s", text)
                        return text
                else:
                    partial = json.loads(recognizer.PartialResult() or "{}")
                    partial_text = (partial.get("partial") or "").strip()
                    if partial_text and speech_started_at is None:
                        speech_started_at = time.monotonic()

                now = time.monotonic()
                if speech_started_at and (now - speech_started_at) > phrase_time_limit:
                    final = json.loads(recognizer.FinalResult() or "{}")
                    text = (final.get("text") or "").strip()
                    return text or None
                if speech_started_at is None and (now - listen_started_at) > timeout:
                    return None
    except Exception as exc:  # noqa: BLE001
        logger.error("Voice capture failed: %s", exc)
        return None
