"""Direct n8n execution cannot confuse transport acceptance with task completion."""
import json
import unittest
from unittest.mock import patch

from executor import n8n_executor as n8n
from core.webhook_safety import validate_webhook_url


class FakeResponse:
    def __init__(self, status=200, body=None, headers=None):
        self.status_code = status
        if body is None:
            self.payload = b""
        elif isinstance(body, bytes):
            self.payload = body
        else:
            self.payload = json.dumps(body).encode("utf-8")
        self.headers = dict(headers or {})
        if body is not None and "Content-Type" not in self.headers:
            self.headers["Content-Type"] = "application/json"

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def iter_content(self, chunk_size=4096):
        for start in range(0, len(self.payload), chunk_size):
            yield self.payload[start:start + chunk_size]


class N8nExecutorTests(unittest.TestCase):
    def test_no_configured_webhook_never_calls_network(self):
        with (
            patch.object(n8n.config, "N8N_WEBHOOK_URL", ""),
            patch.object(n8n.requests, "post") as post,
        ):
            result = n8n.trigger_workflow("news")
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "not_configured")
        post.assert_not_called()

    def test_accepted_http_is_not_claimed_as_workflow_completion(self):
        response = FakeResponse(202, {"reply": "Turned lights on"})
        with (
            patch.object(n8n.config, "N8N_WEBHOOK_URL", "https://example.org/webhook"),
            patch.object(n8n.requests, "post", return_value=response) as post,
        ):
            result = n8n.trigger_workflow("lights", {"room": "bedroom"})
        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "webhook_accepted")
        self.assertIn("NOT independently verified", result["message"])
        self.assertNotIn("Turned lights on", str(result))
        post.assert_called_once()
        self.assertEqual(post.call_args.kwargs["timeout"], (3, 10))
        self.assertFalse(post.call_args.kwargs["allow_redirects"])
        self.assertTrue(post.call_args.kwargs["stream"])

    def test_explicit_workflow_failure_overrides_http_200(self):
        for body in ({"status": "failed"}, {"success": False}, {"status": "rejected"}):
            with self.subTest(body=body):
                with (
                    patch.object(n8n.config, "N8N_WEBHOOK_URL", "https://example.org/webhook"),
                    patch.object(n8n.requests, "post", return_value=FakeResponse(200, body)),
                ):
                    result = n8n.trigger_workflow("news")
                self.assertFalse(result["success"])
                self.assertEqual(result["status"], "workflow_rejected")

    def test_redirects_and_http_error_never_claim_success(self):
        with patch.object(n8n.config, "N8N_WEBHOOK_URL", "https://example.org/webhook"):
            with patch.object(n8n.requests, "post", return_value=FakeResponse(302)):
                self.assertEqual(n8n.trigger_workflow("news")["status"], "redirect_refused")
            with patch.object(n8n.requests, "post", return_value=FakeResponse(500)):
                result = n8n.trigger_workflow("news")
                self.assertFalse(result["success"])
                self.assertEqual(result["status"], "http_error")

    def test_oversized_reply_is_not_treated_as_inspected(self):
        with (
            patch.object(n8n.config, "N8N_WEBHOOK_URL", "https://example.org/webhook"),
            patch.object(n8n.requests, "post", return_value=FakeResponse(200, b"X" * 17000)),
        ):
            result = n8n.trigger_workflow("news")
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "response_too_large")

    def test_too_large_or_unserializable_payload_fails_before_post(self):
        with (
            patch.object(n8n.config, "N8N_WEBHOOK_URL", "https://example.org/webhook"),
            patch.object(n8n.requests, "post") as post,
        ):
            for data in ({"huge": "x" * 20000}, {"invalid": {1, 2}}):
                self.assertFalse(n8n.trigger_workflow("news", data)["success"])
            post.assert_not_called()

    def test_remote_plaintext_and_userinfo_urls_are_denied(self):
        for value in ("http://external.example/hook", "https://user:pass@example.org/hook",
                      "https://example.org:bad/hook", "https://example.org/hook#fragment"):
            with self.subTest(value=value):
                self.assertIsNotNone(validate_webhook_url(value))
        self.assertIsNone(validate_webhook_url("http://127.0.0.1:5678/webhook"))

    def test_network_timeout_is_failed_without_body_exposure(self):
        with (
            patch.object(n8n.config, "N8N_WEBHOOK_URL", "https://example.org/webhook"),
            patch.object(n8n.requests, "post", side_effect=n8n.requests.Timeout),
        ):
            result = n8n.trigger_workflow("news")
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "request_failed")


if __name__ == "__main__":
    unittest.main()
