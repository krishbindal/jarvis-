from __future__ import annotations

"""Executor for triggering n8n workflows via webhook."""

from typing import Any, Dict

import requests

N8N_WEBHOOK_URL = "http://localhost:5678/webhook/jarvis"


def trigger_workflow(action: str, data: Dict[str, Any] | None = None) -> Dict[str, Any]:
    payload = {"action": action, "data": data or {}}
    try:
        resp = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=10)
        resp.raise_for_status()
        try:
            body = resp.json()
        except Exception:  # noqa: BLE001
            body = resp.text
        return {
            "success": True,
            "status": "success",
            "message": f"Triggered n8n workflow '{action}'",
            "output": body or resp.text,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "success": False,
            "status": "error",
            "message": f"n8n workflow trigger failed: {exc}",
        }
