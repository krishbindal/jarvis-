"""Playwright helper must not claim to control an unconnected browser tab."""
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from skills import browser_agent as agent


class BrowserReliabilityTests(unittest.TestCase):
    def test_existing_tab_actions_never_launch_a_fake_blank_page(self):
        for operation in ("scroll", "click_first", "extract"):
            with self.subTest(operation=operation):
                report = agent._run_browser_task(operation, "this page")
                self.assertFalse(report["success"])
                self.assertEqual(report["status"], "existing_tab_unavailable")

    def test_read_current_page_without_url_fails(self):
        with patch.object(agent, "_run_browser_task", wraps=agent._run_browser_task) as task:
            report = agent.execute("read this page")
        self.assertEqual(report["status"], "url_required")
        task.assert_called_once_with("read", "")

    def test_read_explicit_url_routes_correctly(self):
        with patch.object(agent, "_run_browser_task", return_value={"success": False}) as task:
            agent.execute("read this page https://example.com/article")
        task.assert_called_once_with("read", "https://example.com/article")

    def test_navigation_reports_only_browser_handoff(self):
        with patch.object(agent.webbrowser, "open", return_value=True) as browser:
            report = agent.execute("go to example.com")
        self.assertTrue(report["success"])
        self.assertEqual(report["status"], "launch_requested")
        self.assertIn("not verified", report["message"].lower())
        browser.assert_called_once_with("https://example.com")

    def test_invalid_embedded_credentials_are_refused(self):
        with patch.object(agent.webbrowser, "open") as browser:
            report = agent.execute("go to https://alice:secret@example.com/private")
        self.assertFalse(report["success"])
        browser.assert_not_called()

    def test_google_search_encodes_user_text_and_closes_browser(self):
        browser = MagicMock()
        page = browser.new_page.return_value
        page.goto.return_value.status = 200
        heading = MagicMock()
        heading.inner_text.return_value = "Sourced title"
        page.query_selector_all.return_value = [heading]
        runtime = MagicMock()
        runtime.chromium.launch.return_value = browser
        context = MagicMock()
        context.__enter__.return_value = runtime
        fake_api = SimpleNamespace(sync_playwright=lambda: context)
        with patch.dict(sys.modules, {"playwright": MagicMock(), "playwright.sync_api": fake_api}):
            report = agent.execute("search for tea & coffee")
        self.assertTrue(report["success"])
        self.assertEqual(report["status"], "search_headings_observed")
        self.assertIn("tea+%26+coffee", page.goto.call_args.args[0])
        self.assertEqual(report["output"], "Sourced title")
        browser.close.assert_called_once()

    def test_http_failure_is_not_reported_as_success(self):
        browser = MagicMock()
        browser.new_page.return_value.goto.return_value.status = 404
        runtime = MagicMock()
        runtime.chromium.launch.return_value = browser
        context = MagicMock()
        context.__enter__.return_value = runtime
        fake_api = SimpleNamespace(sync_playwright=lambda: context)
        with patch.dict(sys.modules, {"playwright": MagicMock(), "playwright.sync_api": fake_api}):
            report = agent._run_browser_task("read", "https://example.com")
        self.assertFalse(report["success"])
        self.assertEqual(report["status"], "fetch_failed")
        browser.close.assert_called_once()

    def test_empty_search_results_never_claim_search_complete(self):
        browser = MagicMock()
        page = browser.new_page.return_value
        page.goto.return_value.status = 200
        page.query_selector_all.return_value = []
        runtime = MagicMock()
        runtime.chromium.launch.return_value = browser
        context = MagicMock()
        context.__enter__.return_value = runtime
        fake_api = SimpleNamespace(sync_playwright=lambda: context)
        with patch.dict(sys.modules, {"playwright": MagicMock(), "playwright.sync_api": fake_api}):
            report = agent._run_browser_task("search", "rare unfindable phrase")
        self.assertFalse(report["success"])
        self.assertEqual(report["status"], "no_observed_results")
        browser.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
