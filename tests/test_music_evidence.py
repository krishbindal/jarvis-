"""Music execution should not claim success before yt-dlp and mixer evidence."""
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from skills import music_player as music


class MusicExecutionEvidenceTests(unittest.TestCase):
    def test_downloader_nonzero_return_never_claims_success(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(music.subprocess, "run", return_value=SimpleNamespace(returncode=1)) as process:
                result = music._download_audio("example", Path(folder))
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "download_failed")
        self.assertEqual(process.call_args.kwargs["timeout"], 90)
        self.assertFalse(process.call_args.kwargs["check"])

    def test_subprocess_return_zero_without_file_is_not_success(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(music.subprocess, "run", return_value=SimpleNamespace(returncode=0)):
                result = music._download_audio("example", Path(folder))
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "missing_output")

    def test_downloader_success_requires_nonempty_unique_file(self):
        with tempfile.TemporaryDirectory() as folder:
            def write_output(command, **kwargs):
                template = command[command.index("-o") + 1]
                output = Path(template.replace("%(ext)s", "mp3"))
                output.write_bytes(b"fake-mp3-content")
                return SimpleNamespace(returncode=0)
            with patch.object(music.subprocess, "run", side_effect=write_output):
                first = music._download_audio("sample", Path(folder))
                second = music._download_audio("sample", Path(folder))
        self.assertTrue(first["success"])
        self.assertTrue(second["success"])
        self.assertNotEqual(first["path"], second["path"])

    def test_playback_does_not_start_after_download_failure(self):
        fake_pygame = MagicMock()
        with (
            patch.object(music, "_download_audio", return_value={"success": False, "status": "download_failed"}),
            patch.dict(sys.modules, {"pygame": fake_pygame}),
        ):
            result = music.execute("play some music")
        self.assertFalse(result["success"])
        fake_pygame.mixer.music.play.assert_not_called()

    def test_verified_mixer_state_reports_only_observed_playback(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "audio.mp3"
            path.write_bytes(b"test-data")
            fake_pygame = MagicMock()
            fake_pygame.mixer.get_init.return_value = True
            fake_pygame.mixer.music.get_busy.return_value = True
            with (
                patch.object(music, "_download_audio", return_value={"success": True, "path": str(path)}),
                patch.dict(sys.modules, {"pygame": fake_pygame}),
            ):
                result = music.execute("play lofi")
        self.assertTrue(result["success"], result)
        self.assertEqual(result["status"], "mixer_playback_observed")
        self.assertIn("not verified", result["message"].lower())
        fake_pygame.mixer.music.play.assert_called_once()

    def test_no_playback_confirmation_is_a_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "audio.mp3"
            path.write_bytes(b"test-data")
            fake_pygame = MagicMock()
            fake_pygame.mixer.get_init.return_value = True
            fake_pygame.mixer.music.get_busy.return_value = False
            with (
                patch.object(music, "_download_audio", return_value={"success": True, "path": str(path)}),
                patch.dict(sys.modules, {"pygame": fake_pygame}),
            ):
                result = music.execute("play a song")
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "playback_unverified")

    def test_download_returns_existing_observed_path_not_background_thread(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "song.mp3"
            path.write_bytes(b"test-data")
            with (
                patch.object(music, "_download_audio", return_value={"success": True, "path": str(path)}),
                patch("config.DOWNLOAD_DIR", folder),
            ):
                result = music.execute("download music jazz")
        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "file_observed")
        self.assertEqual(result["path"], str(path))
        self.assertIn("not tested", result["message"].lower())

    def test_busy_work_does_not_start_second_operation(self):
        self.assertTrue(music._PLAY_LOCK.acquire(blocking=False))
        try:
            with patch.object(music, "_download_audio") as downloader:
                result = music.execute("play something")
            self.assertFalse(result["success"])
            self.assertEqual(result["status"], "busy")
            downloader.assert_not_called()
        finally:
            music._PLAY_LOCK.release()

    def test_stop_without_playing_does_not_claim_audio_stopped(self):
        fake_pygame = MagicMock()
        fake_pygame.mixer.get_init.return_value = True
        fake_pygame.mixer.music.get_busy.return_value = False
        with patch.dict(sys.modules, {"pygame": fake_pygame}):
            result = music.execute("stop music")
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "not_playing")


if __name__ == "__main__":
    unittest.main()
