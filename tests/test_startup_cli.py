"""Dependency-free bootstrap tests for Jarvis."""
import unittest
from unittest.mock import patch

import main


class StartupArgsTests(unittest.TestCase):
    def test_immediate_ui_is_default(self):
        self.assertFalse(main.parse_args([]).wait_for_clap)

    def test_optional_clap_start(self):
        self.assertTrue(main.parse_args(["--wait-for-clap"]).wait_for_clap)

    def test_maintenance_modes_are_mutually_exclusive(self):
        with self.assertRaises(SystemExit):
            main.parse_args(["--doctor", "--install-autostart"])

    def test_doctor_runs_without_loading_gui(self):
        with patch("utils.diagnostics.run_diagnostics", return_value=True):
            self.assertEqual(main.main(["--doctor"]), 0)
        with patch("utils.diagnostics.run_diagnostics", return_value=False):
            self.assertEqual(main.main(["--doctor"]), 1)


if __name__ == "__main__":
    unittest.main()
