"""A vague command must not silently become executable generated Python."""
import unittest
from unittest.mock import patch

from core import command_router
from core.app import JarvisApp


class RouterSafetyTests(unittest.TestCase):
    def test_unmatched_request_does_not_auto_run_system_agent(self):
        with patch.object(command_router, "match_skill", return_value=None):
            result = command_router._route_single("perform this unfamiliar operation")
        self.assertEqual(result["action"], "unknown")

    def test_generated_code_requires_explicit_wording(self):
        with patch.object(command_router, "match_skill", return_value=None):
            result = command_router._route_single("run generated python to inspect a csv")
        self.assertEqual(result["action"], "skill:system_agent")

    def test_information_request_is_not_a_desktop_action(self):
        self.assertTrue(JarvisApp._looks_like_information_request("explain neural networks"))
        self.assertFalse(JarvisApp._looks_like_information_request("open notepad"))

    def test_ai_answer_is_not_marked_as_verified_action(self):
        with patch("brain.ai_engine.query_ai", return_value="A possible explanation."):
            result = JarvisApp._answer_conversation("explain caching")
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "ai_answer_unverified")
        self.assertIn("not independently verified", result["message"])

    def test_unavailable_ai_is_not_called_a_success(self):
        with patch("brain.ai_engine.query_ai", return_value="Jarvis AI is currently unavailable (No API keys or local model reachable)."):
            result = JarvisApp._answer_conversation("explain caching")
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "unavailable")


if __name__ == "__main__":
    unittest.main()
