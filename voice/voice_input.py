from __future__ import annotations

"""Offline voice input using Vosk and sounddevice."""

import json
import threading
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

# COMMAND_GRAMMAR is no longer used, Vosk will use its full vocabulary 
# to support opening any app.

COMMAND_KEYWORDS = [
    "open", "close", "download", "search",
    "play", "stop", "list", "create", "delete"
]

def clean_text(text: str) -> str:
    words = text.split()
    if len(words) > 3 and all(len(w) == 1 for w in words):
        return "".join(words)
    return text

class VoiceListener:
    def __init__(self, event_bus):
        self._event_bus = event_bus
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
        # Load Vosk Model once
        self.model = None
        self.rec = None
        
        if Model is None:
            logger.error("Vosk dependency missing; cannot initialize VoiceListener.")
            return
            
        model_path = Path(config.VOICE_MODEL_PATH)
        if not model_path.exists():
            logger.error("Voice model not found at %s", model_path)
            return
            
        try:
            self.model = Model(str(model_path))
            # Initializing recognizer without strict grammar limits to allow identifying any installed app
            self.rec = KaldiRecognizer(self.model, 16000)
            logger.info("Vosk VoiceListener initialized successfully.")
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to load Vosk model: %s", exc)

    def _callback(self, indata, frames, time_info, status):
        if status:
            logger.debug("Audio status: %s", status)

        if self.rec and self.rec.AcceptWaveform(bytes(indata)):
            result = json.loads(self.rec.Result())
            text = result.get("text", "").strip()

            if text:
                text = clean_text(text)
                
                # Filter against our generic expected commands
                if any(word in text for word in COMMAND_KEYWORDS):
                    logger.info("✅ Voice Command: %s", text)
                    self._event_bus.emit(
                        "command_received",
                        {"text": text, "source": "voice"}
                    )
                else:
                    logger.debug("❌ Ignored partial/unrelated speech: %s", text)

    def _run(self):
        logger.info("Starting background voice listener.")
        try:
            with sd.RawInputStream(
                samplerate=16000,
                blocksize=8000,
                dtype='int16',
                channels=1,
                callback=self._callback
            ):
                while self._running:
                    # Keep thread alive to process audio stream callbacks
                    sd.sleep(100)
        except Exception as exc:  # noqa: BLE001
            logger.error("Voice listener crashed: %s", exc)

    def start(self):
        if self._running or self.model is None or self.rec is None:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, name="voice-listener-thread", daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
