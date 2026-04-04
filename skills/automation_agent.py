"""
JARVIS-X Phase 26: N8N Automation
Skill: Sends triggers, macros, and Smart Home commands to an external N8N webhook.
"""

import requests
from typing import Any, Dict
from utils.logger import get_logger
import config

logger = get_logger(__name__)

SKILL_NAME = "automation"
SKILL_DESCRIPTION = "Trigger external automated logic and smart home actions via physical webhooks (n8n)"
SKILL_PATTERNS = [
    r"trigger\s+(?:the\s+)?(workflow|macro|automation)\s*(.*)?$",
    r"turn\s+(on|off)\s+(?:the\s+)?(.*)$",
    r"start\s+(?:the\s+)?(?:workflow|macro|n8n)\s*(.*)?$"
]

def execute(target: str, extra: Dict[str, Any] = None) -> Dict[str, Any]:
    """POST intent to configured automation webhook."""
    url = getattr(config, "N8N_WEBHOOK_URL", "")
    
    # Clean target string by passing the raw matched command correctly formatted
    payload = {
        "command": target.strip(),
        "extra_context": extra or {}
    }

    if not url or "your-n8n-url" in url:
        logger.warning("[AUTOMATION] N8N_WEBHOOK_URL is not properly set in .env. Faking local success.")
        # Returning true anyway to gracefully degrade if the user just wants to test the NLP
        return {
            "success": True, 
            "status": "success", 
            "message": "Simulated automation trigger. Configure N8N_WEBHOOK_URL in .env to activate actual smart home routing.", 
            "output": payload
        }
    
    try:
        logger.info(f"[AUTOMATION] Pushing to {url} payload={payload['command']}")
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code in [200, 201]:
            # Try to grab a conversational reply if N8N returns one
            reply = response.json().get("reply", "Automation triggered successfully.") if 'application/json' in response.headers.get('Content-Type', '') else "Automation triggered successfully."
            return {
                "success": True,
                "status": "success",
                "message": reply,
                "output": response.text
            }
        else:
            return {
                "success": False,
                "status": "failed",
                "message": f"Webhook returned HTTP {response.status_code}"
            }
    except Exception as e:
        logger.error(f"[AUTOMATION] Webhook failed: {e}")
        return {
            "success": False,
            "status": "error",
            "message": f"Failed to contact smart home webhook: {e}"
        }
