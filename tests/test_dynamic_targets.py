"""Opening a local file or URL must never infer unobserved success."""
import unittest
from unittest.mock import patch

from core.target_safety import inspect_open_target
from core import action_registry


class TargetValidationTests(unittest.TestCase):
    def test_rejects_script_schemes(self):
        for url in ("javascript:alert(1)", "data:text/html,<script>x</script>",
                    "powershell:do-something", "ms-settings:privacy"):
            with self.subTest(url=url):
                allowed, _, _ = inspect_open_target(url, "url")
                self.assertFalse(allowed)

    def test_only_http_and_https_are_urls(self):
        self.assertTrue(inspect_open_target("https://example.com", "url")[0])
        self.assertFalse(inspect_open_target("file:///C:/secret.txt", "url")[0])
        self.assertFalse(inspect_open_target("ftp://example.com", "url")[0])
        self.assertFalse(inspect_open_target("example.com", "url")[0])

    def test_rejects_credentials_embedded_in_url(self):
        valid, _, _ = inspect_open_target("https://alice:password@example.com", "url")
        self.assertFalse(valid)

    def test_requires_approval_for_local_executable(self):
        for file in ("C:\\Temp\\setup.exe", "C:/Temp/setup.ps1", "C:/Temp/click.lnk"):
            with self.subTest(file=file):
                valid, needs_approval, _ = inspect_open_target(file, "file")
                self.assertTrue(valid)
                self.assertTrue(needs_approval)

    def test_regular_document_does_not_require_executable_consent(self):
        self.assertEqual(inspect_open_target("C:/Documents/report.pdf", "file")[:2], (True, False))

    def test_unsafe_uri_never_reaches_os(self):
        with patch.object(action_registry, "_native_open") as native:
            result = action_registry._open_dynamic_handler(
                "javascript:alert(1)", {"resolved_type": "url"},
            )
        self.assertFalse(result["success"])
        native.assert_not_called()

    def test_executable_requires_user_confirm(self):
        with (
            patch.object(action_registry, "check_action", return_value={
                "success": False, "status": "approval_required", "message": "Denied",
            }) as approve,
            patch.object(action_registry, "_native_open") as native,
        ):
            result = action_registry._open_dynamic_handler("C:/Temp/setup.exe", {"resolved_type": "file"})
        self.assertFalse(result["success"])
        approve.assert_called_once_with("open_executable", "C:/Temp/setup.exe")
        native.assert_not_called()

    def test_browser_rejection_is_not_reported_as_success(self):
        with (
            patch.object(action_registry.webbrowser, "get") as get,
            patch.object(action_registry.webbrowser, "open", return_value=False),
            patch.object(action_registry, "_native_open", side_effect=OSError("not available")),
        ):
            get.return_value.open.return_value = False
            result = action_registry._open_dynamic_handler(
                "https://example.com", {"resolved_type": "url", "app": "chrome"},
            )
        self.assertFalse(result["success"])
        self.assertIn("failed", result["message"].lower())
        self.assertNotIn("after 3 attempts", result["message"])


if __name__ == "__main__":
    unittest.main()
