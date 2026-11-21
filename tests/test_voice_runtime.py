"""Regression checks for audio callback isolation and wake timing."""
import io
import queue
import threading
import unittest
from unittest.mock import MagicMock, patch

from voice.voice_input import VoiceListener


class VoiceRuntimeTests(unittest.TestCase):
    def _listener(self):
        # Construct state without loading hardware, downloading models or opening a mic.
        listener = VoiceListener.__new__(VoiceListener)
        listener._event_bus = MagicMock()
        listener._last_wake_time = 0.0
        listener._listening_for_command = False
        listener._silence_start_ts = 10.0
        listener._max_listen_time = 7.0
        listener._buffer_lock = threading.Lock()
        listener._audio_buffer = io.BytesIO(b"stale audio")
        listener._audio_queue = queue.Queue(maxsize=1)
        listener._dropped_frames = 0
        listener._oww_model = MagicMock()
        listener.ambient_mode = True
        listener._is_jarvis_speaking = False
        listener._last_speaking_ts = 0.0
        listener.rec = MagicMock()
        listener.rec.AcceptWaveform.return_value = False
        return listener

    def test_talk_resets_timeout_after_long_idle(self):
        listener = self._listener()
        with patch("voice.voice_input.time.time", return_value=200.0):
            listener._on_jarvis_wake({"source": "app_internal"})
        self.assertTrue(listener._listening_for_command)
        self.assertEqual(listener._silence_start_ts, 200.0)
        self.assertEqual(listener._audio_buffer.getvalue(), b"")

        with patch("voice.voice_input.time.time", return_value=200.25):
            listener._process_audio(b"\\x00" * 256)
        listener.rec.Result.assert_not_called()

    def test_portaudio_callback_only_queues_frames(self):
        listener = self._listener()
        listener._callback(b"frame", 5, None, None)
        self.assertEqual(listener._audio_queue.get_nowait(), b"frame")
        listener._oww_model.predict.assert_not_called()
        listener.rec.AcceptWaveform.assert_not_called()

    def test_queue_is_bounded_and_drops_overflow(self):
        listener = self._listener()
        listener._callback(b"first", 5, None, None)
        listener._callback(b"second", 6, None, None)
        self.assertEqual(listener._audio_queue.qsize(), 1)
        self.assertEqual(listener._audio_queue.get_nowait(), b"first")
        self.assertEqual(listener._dropped_frames, 1)


if __name__ == "__main__":
    unittest.main()
