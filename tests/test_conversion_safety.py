"""Conversion must respect time bounds and never overwrite existing outputs."""
import subprocess
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from PIL import Image
from executor import conversion_executor as conversion


class ConversionSafetyTests(unittest.TestCase):
    def test_ffmpeg_creates_unique_file_while_preserving_existing_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "sample.wav"
            source.write_bytes(b"fake input")
            existing = root / "sample.mp3"
            existing.write_bytes(b"old file contents")

            def ffmpeg(command, **kwargs):
                Path(command[-1]).write_bytes(b"new mp3")
                return Mock(returncode=0)

            with patch.object(conversion.subprocess, "run", side_effect=ffmpeg) as runner:
                result = conversion.convert_to_mp3(str(source))
            self.assertTrue(result["success"], result)
            self.assertEqual(result["status"], "file_created")
            self.assertEqual(existing.read_bytes(), b"old file contents")
            self.assertEqual(Path(result["path"]).read_bytes(), b"new mp3")
            self.assertNotEqual(result["path"], str(existing))
            self.assertEqual(runner.call_args.kwargs["timeout"], 120)
            self.assertIn("-nostdin", runner.call_args.args[0])
            self.assertNotIn("-y", runner.call_args.args[0])
            self.assertFalse(list(root.glob(".jarvis-convert-*")), "Temporary outputs must be cleaned up")

    def test_ffmpeg_zero_without_file_is_unverified(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "audio.wav"
            source.write_bytes(b"src")
            with patch.object(conversion.subprocess, "run", return_value=Mock(returncode=0)):
                result = conversion.convert_to_mp3(str(source))
            self.assertFalse(result["success"])
            self.assertEqual(result["status"], "output_unverified")
            self.assertFalse((source.with_suffix(".mp3")).exists())

    def test_ffmpeg_timeout_does_not_publish_partial(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "audio.wav"
            source.write_bytes(b"src")
            with patch.object(conversion.subprocess, "run", side_effect=subprocess.TimeoutExpired("ffmpeg", 120)):
                result = conversion.convert_to_mp3(str(source))
            self.assertFalse(result["success"])
            self.assertEqual(result["status"], "timeout")
            self.assertEqual(list(root.glob("*.mp3")), [])

    def test_failed_converter_does_not_publish_final_file(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "audio.wav"
            source.write_bytes(b"src")
            with patch.object(conversion.subprocess, "run", return_value=Mock(returncode=1)):
                result = conversion.convert_to_mp3(str(source))
            self.assertFalse(result["success"])
            self.assertEqual(result["status"], "conversion_failed")
            self.assertFalse(source.with_suffix(".mp3").exists())

    def test_pdf_conversion_creates_pdf_but_preserves_existing_file(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "photo.png"
            Image.new("RGB", (12, 10), (245, 245, 245)).save(source)
            existing = source.with_suffix(".pdf")
            existing.write_bytes(b"existing pdf")
            result = conversion.convert_to_pdf(str(source))
            self.assertTrue(result["success"], result)
            self.assertEqual(existing.read_bytes(), b"existing pdf")
            with Path(result["path"]).open("rb") as stream:
                self.assertEqual(stream.read(5), b"%PDF-")
            self.assertFalse(list(Path(folder).glob(".jarvis-convert-*")))

    def test_pdf_conversion_rejects_invalid_input_without_overwriting(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "photo.txt"
            source.write_text("not a picture")
            target = source.with_suffix(".pdf")
            target.write_bytes(b"existing")
            result = conversion.convert_to_pdf(str(source))
            self.assertFalse(result["success"])
            self.assertEqual(target.read_bytes(), b"existing")


if __name__ == "__main__":
    unittest.main()
