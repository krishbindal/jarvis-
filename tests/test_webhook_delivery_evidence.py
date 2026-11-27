"""n8n acknowledgment != downstream workflow completion."""
import unittest
from unittest.mock import Mock, patch

from skills import automation_agent as agent


class WebhookEvidenceTests(unittest.TestCase):
    def test_unconfigured_webhook_never_claims_success(self):
        with patch.object(agent.config, "N8N_WEBHOOK_URL", ""):
            with patch.object(agent.requests, "post") as post:
                result = agent.execute("turn on bedroom lights")
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "not_configured")
        post.assert_not_called()

    def test_https_acknowledgment_does_not_claim_device_worked(self):
        with (
            patch.object(agent.config, "N8N_WEBHOOK_URL", "https://example.com/webhook"),
            patch.object(agent.requests, "post", return_value=Mock(status_code=202)) as post,
        ):
            result = agent.execute("turn on lights", {"room": "bedroom"})
        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "webhook_accepted")
        self.assertIn("NOT independently verified", result["message"])
        post.assert_called_once()
        self.assertEqual(post.call_args.kwargs["timeout"], (3, 10))
        self.assertFalse(post.call_args.kwargs["allow_redirects"])
        self.assertEqual(post.call_args.kwargs["json"]["command"], "turn on lights")

    def test_unsafe_http_and_credential_url_are_refused(self):
        for url in ("http://external.example/webhook", "https://user:pass@example.com/webhook", "ftp://example.com/path"):
            with self.subTest(url=url):
                with (
                    patch.object(agent.config, "N8N_WEBHOOK_URL", url),
                    patch.object(agent.requests, "post") as post,
                ):
                    result = agent.execute("open the garage")
                self.assertFalse(result["success"])
                post.assert_not_called()

    def test_loopback_http_allowed_for_local_n8n(self):
        with (
            patch.object(agent.config, "N8N_WEBHOOK_URL", "http://127.0.0.1:5678/webhook"),
            patch.object(agent.requests, "post", return_value=Mock(status_code=200)),
        ):
            self.assertEqual(agent.execute("test")["status"], "webhook_accepted")

    def test_redirect_is_not_followed(self):
        with (
            patch.object(agent.config, "N8N_WEBHOOK_URL", "https://example.com/webhook"),
            patch.object(agent.requests, "post", return_value=Mock(status_code=302)) as post,
        ):
            result = agent.execute("turn on lights")
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "redirect_refused")
        self.assertFalse(post.call_args.kwargs["allow_redirects"])

    def test_network_exception_does_not_claim_success(self):
        with (
            patch.object(agent.config, "N8N_WEBHOOK_URL", "https://example.com/webhook"),
            patch.object(agent.requests, "post", side_effect=agent.requests.Timeout),
        ):
            result = agent.execute("turn on lights")
        self.assertEqual(result["status"], "request_failed")
        self.assertFalse(result["success"])

    def test_extra_cannot_be_unbounded_or_non_json(self):
        with (
            patch.object(agent.config, "N8N_WEBHOOK_URL", "https://example.com/webhook"),
            patch.object(agent.requests, "post") as post,
        ):
            for payload in ({"huge": "x" * 20000}, {"not_json": {1, 2}}):
                with self.subTest(payload_type=str(type(payload))):
                    result = agent.execute("test", payload)
                    self.assertFalse(result["success"])
            post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
