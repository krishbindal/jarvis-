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
            payload = json.loads(post_data)
            
            # Expected payload: {"message": "Hello Sir", "type": "notification"}
            message = payload.get("message", "")
            msg_type = payload.get("type", "notification")
            
            if message:
                logger.info("[WEB-SERVER] Received proactive notification: %s", message)
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

class JarvisWebServer:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.server: HTTPServer | None = None
        self.thread: threading.Thread | None = None

    def start(self):
        if not N8N_NOTIFY_TOKEN:
            logger.warning(
                "[WEB-SERVER] Disabled: set N8N_NOTIFY_TOKEN to enable the local "
                "notification server (it is off by default to prevent unauthenticated access)."
            )
            return

        def _run():
            try:
                self.server = HTTPServer((N8N_NOTIFY_HOST, N8N_NOTIFY_PORT), N8NNotificationHandler)
                self.server.event_bus = self.event_bus
                self.server.auth_token = N8N_NOTIFY_TOKEN
                logger.info(
                    "[WEB-SERVER] Listening for n8n notifications on %s:%d (token required)",
                    N8N_NOTIFY_HOST, N8N_NOTIFY_PORT,
                )
                self.server.serve_forever()
            except Exception as exc:
                logger.error("[WEB-SERVER] Server failed: %s", exc)

        self.thread = threading.Thread(target=_run, name="jarvis-web-server", daemon=True)
        self.thread.start()

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
