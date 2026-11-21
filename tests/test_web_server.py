"""Local notification server authorization, bounds and shutdown regression tests."""
import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import unittest
from unittest.mock import MagicMock, patch

import core.web_server as service


class NotificationServerTests(unittest.TestCase):
    def setUp(self):
        self.events = MagicMock()
        self.host = patch.object(service, "N8N_NOTIFY_HOST", "127.0.0.1")
        self.port = patch.object(service, "N8N_NOTIFY_PORT", 0)
        self.token = patch.object(service, "N8N_NOTIFY_TOKEN", "test-secret")
        self.host.start()
        self.port.start()
        self.token.start()
        self.server = service.JarvisWebServer(self.events)
        self.assertTrue(self.server.start())
        port = self.server.server.server_address[1]
        self.endpoint = f"http://127.0.0.1:{port}/"

    def tearDown(self):
        self.server.stop()
        self.server.stop()  # Idempotent cleanup
        self.token.stop()
        self.port.stop()
        self.host.stop()

    def _post(self, payload, token=None):
        headers = {"Content-Type": "application/json"}
        if token is not None:
            headers["X-Jarvis-Token"] = token
        req = Request(self.endpoint, data=payload, headers=headers, method="POST")
        try:
            with urlopen(req, timeout=3) as response:
                return response.status
        except HTTPError as exc:
            return exc.code

    def test_rejects_unauthorized(self):
        valid = json.dumps({"message": "hello"}).encode()
        self.assertEqual(self._post(valid), 401)
        self.assertEqual(self._post(valid, "wrong"), 401)
        self.events.emit.assert_not_called()

    def test_authorized_notification(self):
        body = json.dumps({"message": "hello"}).encode()
        self.assertEqual(self._post(body, "test-secret"), 200)
        self.events.emit.assert_called_once_with("proactive_warning", "hello")

    def test_rejects_oversized_body(self):
        self.assertEqual(self._post(b"x" * (service.MAX_NOTIFY_BODY + 1), "test-secret"), 413)

    def test_rejects_invalid_json(self):
        self.assertEqual(self._post(b"{bad", "test-secret"), 400)
        self.events.emit.assert_not_called()

    def test_rejects_wrong_json_type(self):
        self.assertEqual(self._post(b"[]", "test-secret"), 400)


class DisabledNotificationTests(unittest.TestCase):
    def test_no_token_means_server_never_binds(self):
        with patch.object(service, "N8N_NOTIFY_TOKEN", ""):
            server = service.JarvisWebServer(MagicMock())
            self.assertFalse(server.start())
            self.assertIsNone(server.server)
            server.stop()


if __name__ == "__main__":
    unittest.main()
