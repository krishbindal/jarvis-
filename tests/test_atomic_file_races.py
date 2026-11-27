"""Race-sensitive filesystem operations must never replace someone else's file."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from executor import atomic_files
from executor import system_executor as files
from triggers.file_sorcerer import FileSorceringHandler


class AtomicFilePublicationTests(unittest.TestCase):
    def test_copy_actual_bytes_without_overwriting(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "source.txt"
            existing = root / "other.txt"
            source.write_bytes(b"new content")
            existing.write_bytes(b"keep this")
            with (
                patch.object(files, "_safe_path", side_effect=Path),
                patch.object(files, "_is_safe", return_value=True),
            ):
                result = files.copy_file(str(source), str(existing))
                self.assertFalse(result["success"])
                self.assertEqual(result["status"], "already_exists")
                self.assertEqual(existing.read_bytes(), b"keep this")
                published = files.copy_file(str(source), str(root / "copied.txt"))
            self.assertTrue(published["success"], published)
            self.assertEqual((root / "copied.txt").read_bytes(), b"new content")
            self.assertEqual(source.read_bytes(), b"new content")

    def test_concurrent_destination_creation_blocks_copy_publication(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, destination = root / "source.txt", root / "target.txt"
            source.write_bytes(b"my source")
            def concurrent_writer(staged, target):
                Path(target).write_bytes(b"other writer")
                raise FileExistsError("raced")
            with (
                patch.object(files, "_safe_path", side_effect=Path),
                patch.object(files, "_is_safe", return_value=True),
                patch.object(atomic_files.os, "link", side_effect=concurrent_writer),
            ):
                result = files.copy_file(str(source), str(destination))
            self.assertFalse(result["success"])
            self.assertEqual(result["status"], "already_exists")
            self.assertEqual(destination.read_bytes(), b"other writer")
            self.assertEqual(source.read_bytes(), b"my source")
            self.assertFalse(list(root.glob(".jarvis-copy-*")), "Temporary copy was leaked")

    def test_concurrent_destination_creation_blocks_move_and_rename(self):
        for action in ("move", "rename"):
            with self.subTest(action=action), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                source = root / "source.txt"
                dest = root / "target.txt"
                source.write_bytes(b"source bytes")
                def concurrent_writer(staged, target):
                    Path(target).write_bytes(b"other writer")
                    raise FileExistsError("raced")
                with (
                    patch.object(files, "_safe_path", side_effect=Path),
                    patch.object(files, "_is_safe", return_value=True),
                    patch.object(atomic_files.os, "link", side_effect=concurrent_writer),
                ):
                    result = (
                        files.move_file(str(source), str(dest))
                        if action == "move" else files.rename_file(str(source), dest.name)
                    )
                self.assertEqual(result["status"], "already_exists")
                self.assertFalse(result["success"])
                self.assertEqual(source.read_bytes(), b"source bytes")
                self.assertEqual(dest.read_bytes(), b"other writer")

    def test_move_and_rename_actual_files_preserve_content(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "source.txt"
            source.write_bytes(b"actual bytes")
            with (
                patch.object(files, "_safe_path", side_effect=Path),
                patch.object(files, "_is_safe", return_value=True),
            ):
                moved = files.move_file(str(source), str(root / "moved.txt"))
                renamed = files.rename_file(str(root / "moved.txt"), "renamed.txt")
            self.assertTrue(moved["success"], moved)
            self.assertTrue(renamed["success"], renamed)
            self.assertEqual((root / "renamed.txt").read_bytes(), b"actual bytes")
            self.assertFalse(source.exists())

    def test_rename_rejects_path_traversal_and_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "source.txt"
            source.write_bytes(b"ok")
            with (
                patch.object(files, "_safe_path", side_effect=Path),
                patch.object(files, "_is_safe", return_value=True),
            ):
                self.assertEqual(files.rename_file(str(source), "../other.txt")["status"], "invalid_name")
                self.assertEqual(files.rename_file(str(source), "back\\slash.txt")["status"], "invalid_name")
                self.assertEqual(files.move_file(str(root), str(root / "moved"))["status"], "unsupported")

    def test_failed_source_unlink_reports_partial_instead_of_success(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            src, dst = root / "src.txt", root / "dst.txt"
            src.write_bytes(b"source")
            with (
                patch.object(files, "_safe_path", side_effect=Path),
                patch.object(files, "_is_safe", return_value=True),
                patch.object(Path, "unlink", side_effect=PermissionError("blocked")),
            ):
                result = files.move_file(str(src), str(dst))
            self.assertFalse(result["success"])
            self.assertEqual(result["status"], "partial")
            self.assertEqual(src.read_bytes(), b"source")
            self.assertEqual(dst.read_bytes(), b"source")

    def test_organizer_preserves_competing_destination_and_chooses_next_name(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "report.pdf"
            source.write_bytes(b"new")
            handler = FileSorceringHandler(str(root), MagicMock())
            true_link = os.link
            first = True
            def race_then_link(src, dest):
                nonlocal first
                if first:
                    first = False
                    Path(dest).write_bytes(b"concurrent")
                    raise FileExistsError("raced")
                return true_link(src, dest)
            with patch.object(atomic_files.os, "link", side_effect=race_then_link):
                handler._sort_file(source)
            destdir = root / "Jarvis_Sorted" / "Documents"
            self.assertEqual((destdir / "report.pdf").read_bytes(), b"concurrent")
            self.assertEqual((destdir / "report (1).pdf").read_bytes(), b"new")
            self.assertFalse(source.exists())
            handler.event_bus.emit.assert_called_once()

    def test_organizer_will_not_move_to_outside_symlink_destination(self):
        with tempfile.TemporaryDirectory() as folder, tempfile.TemporaryDirectory() as external:
            root = Path(folder)
            source = root / "report.pdf"
            source.write_bytes(b"keep")
            try:
                (root / "Jarvis_Sorted").symlink_to(external, target_is_directory=True)
            except OSError:
                self.skipTest("This runner does not allow creation of directory symlinks")
            handler = FileSorceringHandler(str(root), MagicMock())
            handler._sort_file(source)
            self.assertTrue(source.is_file())
            self.assertFalse((Path(external) / "Documents" / "report.pdf").exists())
            handler.event_bus.emit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
