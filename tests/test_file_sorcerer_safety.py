"""File organizer must ignore partial downloads and preserve existing data."""
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from triggers.file_sorcerer import FileSorceringHandler


class FileOrganizerSafetyTests(unittest.TestCase):
    def test_partial_download_is_not_moved(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            partial = root / "download.crdownload"
            partial.write_bytes(b"in progress")
            handler = FileSorceringHandler(str(root), MagicMock())
            with patch("triggers.file_sorcerer.time.sleep") as sleep:
                handler.on_created(SimpleNamespace(is_directory=False, src_path=str(partial)))
            self.assertTrue(partial.is_file())
            self.assertFalse((root / "Jarvis_Sorted").exists())
            sleep.assert_not_called()

    def test_collision_preserves_original(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            original = root / "report.pdf"
            original.write_bytes(b"new")
            existing = root / "Jarvis_Sorted" / "Documents" / "report.pdf"
            existing.parent.mkdir(parents=True)
            existing.write_bytes(b"old")
            handler = FileSorceringHandler(str(root), MagicMock())
            handler._sort_file(original)
            self.assertEqual(existing.read_bytes(), b"old")
            self.assertEqual((existing.parent / "report (1).pdf").read_bytes(), b"new")
            self.assertFalse(original.exists())

    def test_renamed_completed_download_is_organized(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            ready = root / "finished.pdf"
            ready.write_bytes(b"ready")
            handler = FileSorceringHandler(str(root), MagicMock())
            with patch("triggers.file_sorcerer.time.sleep"):
                handler.on_moved(SimpleNamespace(is_directory=False, dest_path=str(ready)))
            self.assertFalse(ready.exists())
            self.assertEqual((root / "Jarvis_Sorted" / "Documents" / "finished.pdf").read_bytes(), b"ready")


if __name__ == "__main__":
    unittest.main()
