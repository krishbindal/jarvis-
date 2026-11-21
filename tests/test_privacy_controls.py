"""No cloud transfer or screen capture merely because API keys exist."""
import importlib.util
import io
import os
from pathlib import Path
import threading
import time
import unittest
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]


class PrivacyDefaultsTests(unittest.TestCase):
    def test_all_data_sharing_permissions_default_off(self):
        spec = importlib.util.spec_from_file_location("isolated_privacy_config", ROOT / "config.py")
        mod = importlib.util.module_from_spec(spec)
        keys = {
            "JARVIS_ALLOW_CLOUD_STT": "",
            "JARVIS_ALLOW_CLOUD_VISION": "",
            "JARVIS_ALLOW_CLOUD_CLIPBOARD": "",
            "JARVIS_REMEMBER_CLIPBOARD": "",
            "JARVIS_ALLOW_LOCAL_SCREEN_SNAPSHOTS": "",
        }
        with patch.dict(os.environ, keys):
            spec.loader.exec_module(mod)
        self.assertFalse(mod.ALLOW_CLOUD_STT)
        self.assertFalse(mod.ALLOW_CLOUD_VISION)
        self.assertFalse(mod.ALLOW_CLOUD_CLIPBOARD)
        self.assertFalse(mod.REMEMBER_CLIPBOARD)
        self.assertFalse(mod.ALLOW_LOCAL_SCREEN_SNAPSHOTS)

    def test_screen_description_does_not_capture_when_off(self):
        import brain.ai_engine as engine
        with (
            patch.object(engine, "ALLOW_CLOUD_VISION", False),
            patch.object(engine.os.path, "exists") as exists,
        ):
            result = engine.describe_screen()
        self.assertIn("disabled", result.lower())
        exists.assert_not_called()

    def test_vision_provider_does_not_capture_when_off(self):
        import brain.vision_provider as vision
        provider = vision.VisionProvider()
        with patch.object(vision, "ALLOW_CLOUD_VISION", False):
            self.assertIn("disabled", provider._capture_and_analyze().lower())
            self.assertIsNone(provider.find_element("submit button"))
            provider.start()
            self.assertFalse(provider.is_active)

    def test_clipboard_monitor_does_not_send_or_save_when_not_authorized(self):
        import triggers.clipboard_monitor as clipboard
        monitor = clipboard.ClipboardMonitor(event_bus=MagicMock())
        with (
            patch.object(clipboard, "ALLOW_CLOUD_CLIPBOARD", False),
            patch.object(clipboard, "REMEMBER_CLIPBOARD", False),
            patch.object(clipboard, "query_ai") as cloud,
        ):
            monitor._analyze("password secret ".join(["hello"] * 50))
        cloud.assert_not_called()
        monitor._events.emit.assert_not_called()

    def test_vosk_command_does_not_call_cloud_transcription(self):
        from voice.voice_input import VoiceListener
        import voice.voice_input as module
        listener = VoiceListener.__new__(VoiceListener)
        listener._is_jarvis_speaking = False
        listener._last_speaking_ts = 0.0
        listener.ambient_mode = True
        listener._listening_for_command = True
        listener._silence_start_ts = time.time()
        listener._max_listen_time = 7.0
        listener._buffer_lock = threading.Lock()
        listener._audio_buffer = io.BytesIO()
        listener.rec = MagicMock()
        listener.rec.AcceptWaveform.return_value = True
        listener.rec.Result.return_value = '{"text":"open firefox now"}'
        listener._event_bus = MagicMock()
        finished = threading.Event()
        listener._event_bus.emit.side_effect = lambda name, *a: finished.set() if name == "command_received" else None
        listener._transcribe_online = MagicMock(return_value="cloud transcript")
        with (
            patch.object(module.config, "ALLOW_CLOUD_STT", False),
            patch.object(module.config, "GROQ_API_KEY", "fake-key"),
            patch.object(module, "is_online") as connected,
        ):
            listener._process_audio(b"\0" * 32000)
            self.assertTrue(finished.wait(3), "Vosk command was not delivered")
        connected.assert_not_called()
        listener._transcribe_online.assert_not_called()


if __name__ == "__main__":
    unittest.main()
