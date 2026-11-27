"""Explicit, evidence-based n8n webhook submission.

HTTP acceptance proves only that the configured endpoint accepted a request,
not that a workflow, smart-home device, or downstream automation completed.
"""
from __future__ import annotations

import json
from typing import Any, Dict
from urllib.parse import urlsplit

import requests

import config
from utils.logger import get_logger

logger = get_logger(__name__)

SKILL_NAME = "automation"
SKILL_DESCRIPTION = "Submit a requested event to a configured n8n webhook (no execution verification)"
SKILL_PATTERNS = [
    r"trigger\s+(?:the\s+)?(workflow|macro|automation)\s*(.*)?$",
    r"turn\s+(on|off)\s+(?:the\s+)?(.*)$",
    r"start\s+(?:the\s+)?(?:workflow|macro|n8n)\s*(.*)?$",
    r"(search|download|find)\s+(?:for\s+)?(?:a\s+)?ringtone",
    r"surf\s+(?:the\s+)?web\s+and\s+search\s+for\s+(.+)$",
]

_MAX_COMMAND_CHARS = 2000
_MAX_JSON_BYTES = 16384


def _validate_configured_url(url: Any) -> str | None:
    if not isinstance(url, str) or not url or len(url) > 2048:
        return "No valid n8n webhook URL is configured; no workflow was triggered."
    try:
        parts = urlsplit(url)
        hostname = (parts.hostname or "").lower()
        # HTTPS is mandatory for non-loopback endpoints; credentials in URL
        # are rejected because they can be leaked through logs and proxies.
        if parts.username or parts.password or parts.fragment or not hostname:
            return "n8n webhook URL contains unsupported credentials, fragment or host."
        loopback = hostname in {"localhost", "127.0.0.1", "::1"}
        if parts.scheme != "https" and not (loopback and parts.scheme == "http"):
            return "n8n webhook must use HTTPS except for explicit localhost/loopback."
    except ValueError:
        return "n8n webhook URL is malformed."
    return None


def execute(target: str, extra: Dict[str, Any] = None) -> Dict[str, Any]:
    url = getattr(config, "N8N_WEBHOOK_URL", "")
    issue = _validate_configured_url(url)
    if issue:
        return {"success": False, "status": "not_configured", "message": issue}

    if not isinstance(target, str) or not target.strip() or len(target) > _MAX_COMMAND_CHARS:
        return {
            "success": False, "status": "invalid_command",
            "message": f"Webhook command must be 1–{_MAX_COMMAND_CHARS} characters.",
        }
    if extra is None:
        extra = {}
    if not isinstance(extra, dict):
        return {"success": False, "status": "invalid_parameters", "message": "Webhook extra parameters must be an object."}
    payload = {"command": target.strip(), "extra_context": extra}
    try:
        encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False)
    except (ValueError, TypeError):
        return {"success": False, "status": "invalid_parameters", "message": "Webhook parameters cannot be encoded as JSON."}
    if len(encoded.encode("utf-8")) > _MAX_JSON_BYTES:
        return {"success": False, "status": "too_large", "message": "Webhook parameters exceed the request-size limit."}

    try:
        response = requests.post(
            url, json=payload, timeout=(3, 10), allow_redirects=False,
        )
        status = response.status_code
        if status in (301, 302, 303, 307, 308):
            return {
                "success": False, "status": "redirect_refused",
                "message": "Webhook redirected; Jarvis did not follow an unverified destination.",
            }
        if status not in (200, 201, 202, 204):
            return {
                "success": False, "status": "http_error",
                "message": f"Webhook returned HTTP {status}; downstream execution is not confirmed.",
            }
        logger.info("[AUTOMATION] Webhook acknowledged command, HTTP %d", status)
        return {
            "success": True,
            "status": "webhook_accepted",
            "message": (
                f"Configured n8n webhook acknowledged the request (HTTP {status}). "
                "The workflow and any connected device action were NOT independently verified."
            ),
            "http_status": status,
        }
    except requests.RequestException as exc:
        logger.warning("[AUTOMATION] n8n request failed (%s)", type(exc).__name__)
        return {
            "success": False,
            "status": "request_failed",
            "message": "n8n request failed; workflow execution could not be confirmed.",
        }
