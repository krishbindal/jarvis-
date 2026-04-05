"""
JARVIS-X Phase 20: "Hey Jarvis" Wake Word Detection

Uses openwakeword for local, free, offline wake word detection.
Falls back to a simple keyword-based approach if openwakeword is unavailable.
"""

from __future__ import annotations

import threading
import time
import numpy as np
from typing import Optional

from utils.logger import get_logger

logger = get_logger(__name__)

WAKE_WORD = "hey jarvis"
SAMPLE_RATE = 16000
CHUNK_SIZE = 1280  # 80ms at 16kHz


class WakeWordDetector:
    """Detects the 'Hey Jarvis' wake word using openwakeword or keyword spotting."""

    def __init__(self, event_bus=None, sensitivity: float = 0.5) -> None:
        self._events = event_bus
        self._sensitivity = sensitivity
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._model = None
        self._use_oww = False
        
        # Debouncing and state management
        self._last_trigger_ts = 0.0
        self._cooldown_s = 5.0
        self._is_handling_command = False

        # Try to load openwakeword
        try:
            import openwakeword
            from openwakeword.model import Model

            # Download default models (includes "hey jarvis" compatible ones)
            openwakeword.utils.download_models()
            self._model = Model(
                wakeword_models=["hey_jarvis"],
                inference_framework="onnx",
            )
            self._use_oww = True
            logger.info("[WAKEWORD] openwakeword loaded with 'hey_jarvis' model.")
            
            # Listen for command completion to re-enable wake word
            if self._events:
                self._events.subscribe("command_complete", self._on_command_complete)
                self._events.subscribe("jarvis_wake", self._on_external_wake)
                self._events.subscribe("system_shutdown", self.stop)
        except Exception as e:
            logger.warning("[WAKEWORD] openwakeword not available (%s). Using keyword fallback.", e)
            self._use_oww = False

    def start(self) -> None:
        """Start listening for the wake word."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, name="wake-word", daemon=True)
        self._thread.start()
        logger.info("[WAKEWORD] Detector started (mode=%s)", "openwakeword" if self._use_oww else "keyword")

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        logger.info("[WAKEWORD] Detector stopped.")

    def _listen_loop(self) -> None:
        """Main audio capture loop."""
        try:
            import sounddevice as sd
        except ImportError:
            logger.error("[WAKEWORD] sounddevice not installed.")
            return

        try:
            with sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="int16",
                blocksize=CHUNK_SIZE,
                callback=self._audio_callback,
            ):
                while self._running:
                    time.sleep(0.1)
        except Exception as e:
            logger.error("[WAKEWORD] Audio stream failed: %s", e)

    def _audio_callback(self, indata, frames, time_info, status) -> None:
        """Process each audio chunk for wake word detection."""
        if not self._running:
            return

        if self._use_oww and self._model:
            try:
                # openwakeword expects int16 numpy array
                audio_data = indata[:, 0].copy()
                prediction = self._model.predict(audio_data)

                # Check all model scores
                now = time.monotonic()
                for model_name, score in prediction.items():
                    if score > self._sensitivity:
                        if self._is_handling_command:
                            logger.debug("[WAKEWORD] Ignoring detection: Already listening.")
                            return
                        
                        if now - self._last_trigger_ts < self._cooldown_s:
                            logger.debug("[WAKEWORD] Ignoring detection: Cooldown active.")
                            return

                        logger.info("[WAKEWORD] Detected '%s' (score=%.3f)", model_name, score)
                        self._last_trigger_ts = now
                        self._is_handling_command = True
                        self._on_wake_detected()
                        self._model.reset()  # Reset to avoid repeat triggers
                        return
            except Exception as e:
                logger.debug("[WAKEWORD] Prediction error: %s", e)
        # Keyword fallback is handled by the voice input system

    def _on_wake_detected(self) -> None:
        """Fire when wake word is detected."""
        if self._events:
            self._events.emit("interrupt_tts")
            self._events.emit("jarvis_wake")
            # Also signal overlay
            self._events.emit("overlay_state", {"state": "listening", "text": "Hey Jarvis!"})

        # Play activation sound
        try:
            from utils.notifications import notify
            notify("🎤 Jarvis Activated", "Listening for your command...")
        except Exception:
            pass

    def _on_command_complete(self, payload=None) -> None:
        """Reset state when command finishes."""
        self._is_handling_command = False
        logger.debug("[WAKEWORD] System ready for next wake word.")

    def _on_external_wake(self, payload=None) -> None:
        """Track activation from other sources (e.g., clap)."""
        self._is_handling_command = True
        self._last_trigger_ts = time.monotonic()
