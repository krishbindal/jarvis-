"""n8n webhooks: report observed HTTP acknowledgments, never implied execution."""
from __future__ import annotations

import json
from typing import Any, Dict

import requests

import config
from core.webhook_safety import validate_webhook_url
from utils.logger import get_logger

logger = get_logger(__name__)
_MAX_REQUEST_BYTES = 16 * 1024
_MAX_RESPONSE_BYTES = 16 * 1024
_ACCEPTED = {200, 201, 202, 204}
_REDIRECTS = {301, 302, 303, 307, 308}


def trigger_workflow(action: str, data: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Submit to the configured endpoint; never claim the workflow finished."""
    url = getattr(config, "N8N_WEBHOOK_URL", "")
    problem = validate_webhook_url(url)
    if problem:
        return {"success": False, "status": "not_configured", "message": problem}

    if not isinstance(action, str) or not action.strip() or len(action) > 200 or any(c in action for c in "\x00\r\n"):
        return {"success": False, "status": "invalid_action", "message": "A valid workflow action of 1–200 characters is required."}
    if data is None:
        data = {}
    if not isinstance(data, dict):
        return {"success": False, "status": "invalid_payload", "message": "Workflow data must be an object."}
    payload = {"action": action.strip(), "data": data}
    try:
        encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError):
        return {"success": False, "status": "invalid_payload", "message": "Workflow data could not be encoded as JSON."}
    if len(encoded.encode("utf-8")) > _MAX_REQUEST_BYTES:
        return {"success": False, "status": "too_large", "message": "Workflow payload exceeds the allowed request size."}

    try:
        with requests.post(
            url, json=payload, timeout=(3, 10),
            allow_redirects=False, stream=True,
        ) as response:
            status_code = response.status_code
            if status_code in _REDIRECTS:
                return {
                    "success": False, "status": "redirect_refused",
                    "message": "Webhook redirected; Jarvis refused to contact a new destination.",
                }
            if status_code not in _ACCEPTED:
                return {
                    "success": False, "status": "http_error",
                    "message": f"n8n returned HTTP {status_code}; no workflow completion was verified.",
                }

            # Response data is untrusted. Only parse a small body to detect
            # explicit failure flags; never feed it into the next tool's target.
            content_length = response.headers.get("Content-Length", "")
            try:
                if content_length and int(content_length) > _MAX_RESPONSE_BYTES:
                    return {
                        "success": False, "status": "response_too_large",
                        "message": "Webhook acknowledged but returned an oversized response that was not inspected.",
                    }
            except ValueError:
                return {"success": False, "status": "invalid_response", "message": "Webhook response has invalid Content-Length."}

            raw = bytearray()
            for chunk in response.iter_content(chunk_size=4096):
                if not chunk:
                    continue
                raw.extend(chunk)
                if len(raw) > _MAX_RESPONSE_BYTES:
                    return {
                        "success": False, "status": "response_too_large",
                        "message": "Webhook response exceeded the safe inspection limit.",
                    }

            if raw and "application/json" in response.headers.get("Content-Type", "").lower():
                try:
                    body = json.loads(raw.decode("utf-8"))
                except (ValueError, UnicodeDecodeError):
                    body = None
                if isinstance(body, dict):
                    flag = body.get("status", "")
                    if body.get("success") is False or (
                        isinstance(flag, str) and flag.lower() in {"error", "failed", "failure", "rejected"}
                    ):
                        return {
                            "success": False, "status": "workflow_rejected",
                            "message": "n8n acknowledged the request but explicitly reported a workflow failure.",
                        }

            logger.info("[N8N] HTTP %d acknowledgment received", status_code)
            return {
                "success": True,
                "status": "webhook_accepted",
                "message": (
                    f"n8n webhook acknowledged the request (HTTP {status_code}). "
                    "Workflow completion and connected device state were NOT independently verified."
                ),
                "http_status": status_code,
            }
    except requests.RequestException as exc:
        logger.warning("[N8N] Webhook request failed (%s)", type(exc).__name__)
        return {
            "success": False, "status": "request_failed",
            "message": "n8n webhook request failed; no workflow completion was confirmed.",
        }
