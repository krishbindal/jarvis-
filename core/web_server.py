from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import TYPE_CHECKING
from utils.logger import get_logger
from config import N8N_NOTIFY_HOST, N8N_NOTIFY_PORT, N8N_NOTIFY_TOKEN

if TYPE_CHECKING:
    from utils.events import EventBus

logger = get_logger(__name__)

MAX_NOTIFY_BODY = 64 * 1024  # 64 KB cap on inbound payloads


class N8NNotificationHandler(BaseHTTPRequestHandler):
    def _authorized(self) -> bool:
        """Require a matching shared-secret token on every request."""
        import hmac
        expected = getattr(self.server, "auth_token", "")
        if not expected:
            return False
        provided = self.headers.get("X-Jarvis-Token", "")
        return hmac.compare_digest(provided, expected)

    def do_POST(self):
        """Handle incoming notifications from n8n."""
        try:
            if not self._authorized():
                logger.warning("[WEB-SERVER] Rejected unauthorized notification request.")
                self.send_response(401)
                self.end_headers()
                return

            content_length = int(self.headers.get('Content-Length', 0))
            if content_length <= 0 or content_length > MAX_NOTIFY_BODY:
                self.send_response(413)
                self.end_headers()
                return
            post_data = self.rfile.read(content_length)
            try:
                payload = json.loads(post_data)
            except (ValueError, UnicodeDecodeError):
                self.send_response(400)
                self.end_headers()
                return
            if not isinstance(payload, dict):
                self.send_response(400)
                self.end_headers()
                return

            message = payload.get("message", "")
            if not isinstance(message, str) or len(message) > 2048:
                self.send_response(400)
                self.end_headers()
                return

            if message:
                logger.info("[WEB-SERVER] Received authenticated notification (%d chars)", len(message))
                # Global access to EventBus or passed in via server
                self.server.event_bus.emit("proactive_warning", message)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success"}).encode())
            else:
                self.send_response(400)
                self.end_headers()
        except Exception as exc:
            logger.error("[WEB-SERVER] Error handling POST: %s", exc)
            self.send_response(500)
            self.end_headers()

    def log_message(self, format, *args):
        # Suppress standard logging to avoid cluttering the terminal
        return

class _BoundedHTTPServer(HTTPServer):
    """Apply a per-client read timeout, including to partial HTTP requests."""

    def get_request(self):
        request, address = super().get_request()
        request.settimeout(5)
        return request, address


class JarvisWebServer:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.server: HTTPServer | None = None
        self.thread: threading.Thread | None = None

    def start(self) -> bool:
        if not N8N_NOTIFY_TOKEN:
            logger.info("[WEB-SERVER] Disabled: configure N8N_NOTIFY_TOKEN to opt in.")
            return False
        if self.server is not None:
            return True
        try:
            # Bind synchronously so shutdown cannot race an unstarted server.
            server = _BoundedHTTPServer((N8N_NOTIFY_HOST, N8N_NOTIFY_PORT), N8NNotificationHandler)
            server.event_bus = self.event_bus
            server.auth_token = N8N_NOTIFY_TOKEN
            self.server = server
            self.thread = threading.Thread(
                target=server.serve_forever, name="jarvis-web-server", daemon=True
            )
            self.thread.start()
            logger.info(
                "[WEB-SERVER] Listening for n8n on %s:%d (token required)",
                *server.server_address,
            )
            return True
        except Exception as exc:
            logger.error("[WEB-SERVER] Cannot start: %s", exc)
            self.server = None
            return False

    def stop(self) -> None:
        server = self.server
        if server is None:
            return
        self.server = None
        server.shutdown()
        server.server_close()
        if self.thread is not None and self.thread is not threading.current_thread():
            self.thread.join(timeout=3)
        self.thread = None
