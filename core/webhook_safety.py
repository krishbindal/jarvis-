"""Fail-closed validation for configured n8n/webhook endpoints."""
from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit


def validate_webhook_url(url: Any) -> str | None:
    """Allow remote HTTPS and explicit local HTTP only (credentials forbidden)."""
    if not isinstance(url, str) or not url or len(url) > 2048:
        return "No valid n8n webhook URL is configured; no workflow was triggered."
    if any(char.isspace() for char in url):
        return "n8n webhook URL must not include whitespace or control characters."
    try:
        parts = urlsplit(url)
        hostname = (parts.hostname or "").lower()
        port = parts.port  # Force validation of malformed integer ports.
        if parts.username or parts.password or parts.fragment or not hostname:
            return "n8n webhook URL contains unsupported credentials, fragment or host."
        if port is not None and not (1 <= port <= 65535):
            return "n8n webhook port is invalid."
        loopback = hostname in {"localhost", "127.0.0.1", "::1"}
        if parts.scheme != "https" and not (loopback and parts.scheme == "http"):
            return "n8n webhook must use HTTPS except for explicit localhost/loopback."
    except ValueError:
        return "n8n webhook URL is malformed."
    return None
