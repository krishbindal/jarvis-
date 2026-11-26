"""Filesystem postconditions and OS launch responses must be checked."""
import tempfile
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

from executor import system_executor as executor


class FilesystemOutcomeTests(unittest.TestCase):
    def test_create_copy_move_rename_delete_verify_real_files(self):
        with (
            tempfile.TemporaryDirectory() as temp,
            patch.object(executor, "_safe_path", side_effect=lambda path: Path(path)),
            patch.object(executor, "_is_safe", return_value=True),
        ):
            root = Path(temp)
            folder = executor.create_folder("tasks", str(root))
            self.assertTrue(folder["success"], folder)
            self.assertTrue((root / "tasks").is_dir())

            source = root / "tasks" / "source.txt"
            source.write_text("real bytes here", encoding="utf-8")
            copy = executor.copy_file(str(source), str(root / "tasks" / "copied.txt"))
            self.assertTrue(copy["success"], copy)
            self.assertEqual((root / "tasks" / "copied.txt").read_text(), "real bytes here")

            moved = executor.move_file(str(root / "tasks" / "copied.txt"), str(root / "tasks" / "moved.txt"))
            self.assertTrue(moved["success"], moved)
            self.assertTrue((root / "tasks" / "moved.txt").is_file())

            renamed = executor.rename_file(str(root / "tasks" / "moved.txt"), "renamed.txt")
            self.assertTrue(renamed["success"], renamed)
            self.assertTrue((root / "tasks" / "renamed.txt").is_file())

            deleted = executor.delete_file(str(root / "tasks" / "renamed.txt"))
            self.assertTrue(deleted["success"], deleted)
            self.assertFalse((root / "tasks" / "renamed.txt").exists())

    def test_move_copy_and_rename_refuse_overwriting_existing_files(self):
        with (
            tempfile.TemporaryDirectory() as temp,
            patch.object(executor, "_safe_path", side_effect=lambda path: Path(path)),
            patch.object(executor, "_is_safe", return_value=True),
        ):
            root = Path(temp)
            source = root / "source.txt"
            dest = root / "existing.txt"
            source.write_text("original source", encoding="utf-8")
            dest.write_text("keep this", encoding="utf-8")

            for action in (
                lambda: executor.copy_file(str(source), str(dest)),
                lambda: executor.move_file(str(source), str(dest)),
                lambda: executor.rename_file(str(source), "existing.txt"),
            ):
                result = action()
                self.assertFalse(result["success"], result)
                self.assertEqual(result["status"], "already_exists")
                self.assertEqual(source.read_text(encoding="utf-8"), "original source")
                self.assertEqual(dest.read_text(encoding="utf-8"), "keep this")

    def test_copy_does_not_claim_success_when_destination_is_missing(self):
        with (
            tempfile.TemporaryDirectory() as temp,
            patch.object(executor, "_safe_path", side_effect=lambda path: Path(path)),
            patch.object(executor, "_is_safe", return_value=True),
            patch.object(executor.shutil, "copy2", return_value=None),
        ):
            source = Path(temp) / "source.txt"
            source.write_text("actual content", encoding="utf-8")
            result = executor.copy_file(str(source), str(Path(temp) / "missing.txt"))
            self.assertFalse(result["success"])
            self.assertEqual(result["status"], "verification_failed")


class NativeActionOutcomeTests(unittest.TestCase):
    def test_chrome_rejection_does_not_claim_it_was_launched(self):
        with (
            patch.object(executor, "IS_WINDOWS", False),
            patch("webbrowser.get") as browser,
            patch.object(executor, "_native_open", side_effect=OSError("not installed")),
        ):
            browser.return_value.open.return_value = False
            response = executor.open_app("chrome")
        self.assertFalse(response["success"])
        self.assertNotIn("Chrome launched", response["message"])

    def test_windows_lock_request_failure_is_reported(self):
        windows = MagicMock()
        windows.windll.user32.LockWorkStation.return_value = 0
        with patch.object(executor, "IS_WINDOWS", True), patch.object(executor, "ctypes", windows):
            response = executor.power_state("lock")
        self.assertFalse(response["success"])

    def test_windows_sleep_nonzero_return_code_is_failure(self):
        with (
            patch.object(executor, "IS_WINDOWS", True),
            patch.object(executor, "ctypes", MagicMock()),
            patch.object(executor.subprocess, "run", return_value=MagicMock(returncode=1)) as run,
        ):
            response = executor.power_state("sleep")
        self.assertFalse(response["success"])
        run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
