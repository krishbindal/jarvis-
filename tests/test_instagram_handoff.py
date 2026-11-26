"""Instagram must distinguish an accepted launch from an actual loaded profile."""
import unittest
from unittest.mock import patch

from skills import instagram_skill as skill


class InstagramLaunchTests(unittest.TestCase):
    def test_command_prefix_is_not_part_of_username(self):
        self.assertEqual(skill._parse_username("open instagram for @example.user"), "example.user")
        self.assertEqual(skill._parse_username("instagram"), "")
        self.assertIsNone(skill._parse_username("instagram for /sensitive/path"))

    def test_native_launch_handoff_is_not_claimed_as_page_loaded(self):
        with patch.object(skill.os, "startfile", create=True) as native:
            result = skill.execute("instagram for @sample")
        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "launch_requested")
        self.assertIn("not verified", result["message"])
        native.assert_called_once_with("instagram://user?username=sample")

    def test_native_failure_fallback_false_is_a_failure(self):
        with (
            patch.object(skill.os, "startfile", create=True, side_effect=OSError("missing app")),
            patch.object(skill.webbrowser, "open", return_value=False) as browser,
        ):
            result = skill.execute("open instagram for example")
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "open_failed")
        browser.assert_called_once_with("https://www.instagram.com/example/")

    def test_browser_accepted_is_only_launch_request(self):
        with (
            patch.object(skill.os, "startfile", create=True, side_effect=OSError("missing app")),
            patch.object(skill.webbrowser, "open", return_value=True),
        ):
            result = skill.execute("insta @example.user")
        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "browser_open_requested")
        self.assertIn("not verified", result["message"])

    def test_invalid_username_refused_before_browser_or_os(self):
        with (
            patch.object(skill.os, "startfile", create=True) as native,
            patch.object(skill.webbrowser, "open") as browser,
        ):
            result = skill.execute("instagram for ../../evil")
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "invalid_username")
        native.assert_not_called()
        browser.assert_not_called()


if __name__ == "__main__":
    unittest.main()
