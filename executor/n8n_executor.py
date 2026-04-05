from __future__ import annotations

"""Executor for triggering n8n workflows via webhook."""

from typing import Any, Dict

import requests
from utils.logger import get_logger
from config import N8N_WEBHOOK_URL, REQUEST_TIMEOUT

logger = get_logger(__name__)


def trigger_workflow(action: str, data: Dict[str, Any] | None = None) -> Dict[str, Any]:
    payload = {"action": action, "data": data or {}}
    try:
        logger.info("Triggering n8n workflow: %s", action)
        resp = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        try:
            body = resp.json()
            # Advanced n8n response parsing (Phase 33)
            # Handle arrays, nested objects, and direct 'response' keys
            if isinstance(body, list) and len(body) > 0:
                item = body[0]
                if isinstance(item, dict) and "response" in item:
                    out_msg = str(item["response"])
                elif isinstance(item, dict) and "text" in item:
                    out_msg = str(item["text"])
                else:
                    out_msg = f"Sir, I've received a list of {len(body)} items from the automation hub."
            elif isinstance(body, dict) and "response" in body:
                out_msg = str(body["response"])
            elif isinstance(body, dict) and "message" in body:
                out_msg = str(body["message"])
            else:
                out_msg = f"Triggered n8n workflow '{action}' successfully."
        except Exception:  # noqa: BLE001
            body = resp.text
            out_msg = f"Triggered n8n workflow '{action}'"
            
        return {
            "success": True,
            "status": "success",
            "message": out_msg,
            "output": body,
        }
    except requests.Timeout:
        logger.error("n8n workflow trigger timed out for %s", action)
        return {
            "success": False,
            "status": "error",
            "output": "Request timed out",
            "message": "Request timed out",
        }
    except Exception as exc:  # noqa: BLE001
        logger.error("n8n workflow trigger failed for %s: %s", action, exc)
        return {
            "success": False,
            "status": "error",
            "message": f"n8n workflow trigger failed: {exc}",
        }
