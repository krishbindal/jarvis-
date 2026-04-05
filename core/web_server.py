from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import TYPE_CHECKING
from utils.logger import get_logger
from config import N8N_NOTIFY_PORT

if TYPE_CHECKING:
    from utils.events import EventBus

logger = get_logger(__name__)

class N8NNotificationHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        """Handle incoming notifications from n8n."""
        try:
            content_length = int(self.headers['Content-Length'])
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
        def _run():
            try:
                self.server = HTTPServer(('localhost', N8N_NOTIFY_PORT), N8NNotificationHandler)
                self.server.event_bus = self.event_bus
                logger.info("[WEB-SERVER] Listening for n8n notifications on port %d", N8N_NOTIFY_PORT)
                self.server.serve_forever()
            except Exception as exc:
                logger.error("[WEB-SERVER] Server failed: %s", exc)

        self.thread = threading.Thread(target=_run, name="jarvis-web-server", daemon=True)
        self.thread.start()

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
