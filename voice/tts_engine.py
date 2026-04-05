"""
JARVIS-X Phase 18: Premium TTS Engine (The "Voice")

Uses Microsoft Edge TTS (free, no API key) with high-quality neural voices.
Integrates with the EventBus to signal overlay state changes (speaking/idle).
"""

import asyncio
import tempfile
import os
import threading
import sys
import types
from utils.logger import get_logger

try:
    import edge_tts  # type: ignore
    _EDGE_AVAILABLE = True
except Exception:  # noqa: BLE001
    edge_tts = None
    _EDGE_AVAILABLE = False

try:
    import pygame  # type: ignore
    _PYGAME_AVAILABLE = True
except Exception:  # noqa: BLE001
    pygame = types.SimpleNamespace()
    pygame.mixer = types.SimpleNamespace(
        get_init=lambda: True,
        pre_init=lambda *_, **__: None,
        init=lambda *_, **__: None,
        music=types.SimpleNamespace(
            get_busy=lambda: False,
            get_volume=lambda: 1.0,
            set_volume=lambda *_, **__: None,
        ),
        Sound=lambda *_, **__: types.SimpleNamespace(),
        Channel=lambda *_, **__: types.SimpleNamespace(
            play=lambda *_, **__: None,
            get_busy=lambda: False,
            stop=lambda *_, **__: None,
        ),
    )
    pygame.time = types.SimpleNamespace(Clock=lambda: types.SimpleNamespace(tick=lambda *_, **__: None))
    sys.modules["pygame"] = pygame
    _PYGAME_AVAILABLE = False

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
        if not _EDGE_AVAILABLE:
            logger.warning("[TTS] Edge TTS unavailable; skipping synthesis.")
            return
        communicate = edge_tts.Communicate(text, VOICE, rate=RATE, pitch=PITCH)
        await communicate.save(output_file)

    def speak(self, text: str) -> None:
        """Thread-safe call to speak text with overlay state signaling and audio ducking."""
        if not text:
            return
        if not _EDGE_AVAILABLE:
            logger.warning("[TTS] Edge TTS not installed; continuing without synthesis for '%s'", text)
            self._simulate_ducking(text)

        self._is_speaking = True
        # Signal overlay: speaking IMMEDIATELY (to help VoiceListener with echo cancellation)
        if self._events:
            self._events.emit("overlay_state", {
                "state": "speaking",
                "text": text[:40]
            })

        def _speak_thread():
            with self._lock:
                if not text.strip():
                    return

                try:
                    # Defensive: Ensure mixer is still alive
                    if not pygame.mixer.get_init():
                        pygame.mixer.init()

                    # 1. Generate Audio
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
                        tmp_path = tmp.name

                    asyncio.run(self._synthesize(text, tmp_path))

                    # 2. Audio Ducking — Lower music volume if active
                    ducking_applied = False
                    old_music_vol = 1.0
                    if pygame.mixer.music.get_busy():
                        old_music_vol = pygame.mixer.music.get_volume()
                        pygame.mixer.music.set_volume(old_music_vol * 0.2) # Drop to 20%
                        ducking_applied = True

                    # 3. Play as Sound on a dedicated channel
                    sound = pygame.mixer.Sound(tmp_path)
                    channel = pygame.mixer.Channel(0)
                    channel.play(sound)
                    
                    self._interrupted = False
                    # Wait for sound to finish
                    while channel.get_busy():
                        if self._interrupted:
                            channel.stop()
                            break
                        pygame.time.Clock().tick(10)

                except Exception as e:
                    logger.error(f"TTS Synthesis failed: {e}")
                finally:
                    # 4. Restore Music Volume if we ducked it
                    if ducking_applied:
                        try:
                            pygame.mixer.music.set_volume(old_music_vol)
                        except Exception:
                            pass
                            
                    self._is_speaking = False
                    if self._events:
                        self._events.emit("overlay_state", {"state": "IDLE"})
                    # 5. Cleanup temp file
                    if os.path.exists(tmp_path):
                        try:
                            os.remove(tmp_path)
                        except Exception:
                            pass

                    # Signal overlay: back to idle
                    if self._events:
                        self._events.emit("overlay_state", {"state": "idle"})

        threading.Thread(target=_speak_thread, daemon=True).start()

    def _simulate_ducking(self, text: str) -> None:
        """If TTS backend is missing, still practice ducking to keep UX consistent."""
        try:
            ducking_applied = False
            old_music_vol = 1.0
            if hasattr(pygame, "mixer") and pygame.mixer.music.get_busy():
                old_music_vol = pygame.mixer.music.get_volume()
                pygame.mixer.music.set_volume(old_music_vol * 0.2)
                ducking_applied = True

            if ducking_applied:
                pygame.mixer.music.set_volume(old_music_vol)
            logger.debug("[TTS] Simulated ducking for '%s' (no backend available).", text)
        except Exception:
            logger.debug("[TTS] Ducking simulation skipped.")

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
