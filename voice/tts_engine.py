"""
JARVIS-X Phase 18: Premium TTS Engine (The "Voice")

Uses Microsoft Edge TTS (free, no API key) with high-quality neural voices.
Integrates with the EventBus to signal overlay state changes (speaking/idle).
"""

import asyncio
import edge_tts
import pygame
import tempfile
import os
import threading
from utils.logger import get_logger

logger = get_logger(__name__)

# Premium voice options:
#   en-GB-RyanNeural     — British male (JARVIS classic)
#   en-US-GuyNeural      — American male (calm professional)
#   en-IN-PrabhatNeural  — Indian English male
#   en-GB-SoniaNeural    — British female (Friday style)
VOICE = "en-GB-RyanNeural"
RATE = "+5%"     # Slightly faster for responsiveness
PITCH = "+0Hz"   # Natural pitch


class TTSEngine:
    """Asynchronous TTS engine using Edge-TTS and Pygame with overlay integration."""

    def __init__(self, event_bus=None) -> None:
        try:
            if not pygame.mixer.get_init():
                # Standard audio parameters for maximum compatibility:
                # frequency=44100 (CD quality), size=-16 (16-bit signed), channels=2 (stereo), buffer=2048
                pygame.mixer.pre_init(44100, -16, 2, 2048)
                pygame.mixer.init()
                logger.info("[TTS] Audio mixer initialized successfully (44.1kHz, 16-bit, stereo).")
        except Exception as e:
            logger.error(f"[TTS] Initial audio mixer init failed: {e}. Attempting fallback.")
            try:
                pygame.mixer.init()
            except Exception as e2:
                logger.critical(f"[TTS] All audio mixer init attempts failed: {e2}")

        self._lock = threading.Lock()
        self._is_speaking = False
        self._interrupted = False
        self._events = event_bus
        
        if self._events:
            self._events.subscribe("interrupt_tts", self.stop)

    @property
    def is_speaking(self) -> bool:
        return self._is_speaking

    async def _synthesize(self, text: str, output_file: str) -> None:
        """Generate speech audio file using Edge TTS."""
        communicate = edge_tts.Communicate(text, VOICE, rate=RATE, pitch=PITCH)
        await communicate.save(output_file)

    def speak(self, text: str) -> None:
        """Thread-safe call to speak text with overlay state signaling."""
        if not text:
            return

        def _speak_thread():
            with self._lock:
                self._is_speaking = True

                # Signal overlay: speaking
                if self._events:
                    self._events.emit("overlay_state", {
                        "state": "speaking",
                        "text": text[:40]
                    })

                try:
                    # Defensive: Ensure mixer is still alive before synthesis
                    if not pygame.mixer.get_init():
                        logger.warning("[TTS] Mixer was closed unexpectedly. Re-initializing...")
                        try:
                            pygame.mixer.pre_init(44100, -16, 2, 2048)
                            pygame.mixer.init()
                        except Exception as mix_err:
                            logger.error(f"[TTS] Failed to re-initialize mixer: {mix_err}")
                            return

                    # 1. Generate Audio
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
                        tmp_path = tmp.name

                    asyncio.run(self._synthesize(text, tmp_path))

                    # 2. Play Audio
                    pygame.mixer.music.load(tmp_path)
                    pygame.mixer.music.play()
                    self._interrupted = False

                    while pygame.mixer.music.get_busy():
                        if self._interrupted:
                            pygame.mixer.music.stop()
                            break
                        pygame.time.Clock().tick(10)

                    # 3. Cleanup
                    pygame.mixer.music.unload()
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)

                except Exception as e:
                    logger.error(f"TTS Synthesis failed: {e}")
                finally:
                    self._is_speaking = False
                    # Signal overlay: back to idle
                    if self._events:
                        self._events.emit("overlay_state", {"state": "idle"})

        threading.Thread(target=_speak_thread, daemon=True).start()

    def stop(self) -> None:
        """Stop any active playback immediately."""
        self._interrupted = True
        try:
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
        except Exception:
            pass


# Global instance
_engine = None
_event_bus_ref = None


def init_tts(event_bus=None) -> None:
    """Initialize the TTS engine with an optional event bus for overlay integration."""
    global _engine, _event_bus_ref
    _event_bus_ref = event_bus
    _engine = TTSEngine(event_bus=event_bus)


def speak(text: str) -> None:
    """Speak text using the global TTS engine."""
    global _engine
    if _engine is None:
        _engine = TTSEngine(event_bus=_event_bus_ref)
    _engine.speak(text)
