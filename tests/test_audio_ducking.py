"""Deterministic TTS ducking test that does not require real audio hardware."""
import time
import unittest
from unittest.mock import AsyncMock, MagicMock, patch


class TestAudioDucking(unittest.TestCase):
    def test_ducking_logic(self):
        # TTS must be a real coroutine and mixer readiness must be simulated.
        with (
            patch("pygame.mixer.get_init", return_value=(44100, -16, 2)),
            patch("pygame.mixer.init"),
            patch("pygame.mixer.music.get_busy", return_value=True),
            patch("pygame.mixer.music.get_volume", return_value=0.8),
            patch("pygame.mixer.music.set_volume") as set_volume,
            patch("pygame.mixer.Sound", return_value=MagicMock()),
            patch("pygame.mixer.Channel") as channel_factory,
            patch("voice.tts_engine.TTSEngine._synthesize", new_callable=AsyncMock),
        ):
            from voice.tts_engine import TTSEngine

            channel = MagicMock()
            channel_factory.return_value = channel
            channel.get_busy.side_effect = [True, False]
            engine = TTSEngine()
            engine.speak("Test")

            # Wait for the background playback thread, with a bounded deadline.
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline and engine.is_speaking:
                time.sleep(0.02)

            self.assertFalse(engine.is_speaking, "TTS background thread did not finish")
            set_volume.assert_any_call(0.8 * 0.2)
            set_volume.assert_any_call(0.8)
            channel.play.assert_called_once()


if __name__ == "__main__":
    unittest.main()
