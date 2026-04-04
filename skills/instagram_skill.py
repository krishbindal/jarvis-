"""
JARVIS-X Phase 27.5: Native Instagram Integration
Skill: Launches the Instagram Desktop App on Windows.
"""

import os
import threading
from typing import Any, Dict
from utils.logger import get_logger

logger = get_logger(__name__)

SKILL_NAME = "instagram"
SKILL_DESCRIPTION = "Open profiles or the home feed on the native Instagram Desktop app."
SKILL_PATTERNS = [
    r"(?:open\s+)?instagram\s*(?:for\s+)?(.*)?$",
    r"insta\s*(.*)?$"
]

def execute(target: str, extra: Dict[str, Any] = None) -> Dict[str, Any]:
    """Launch Instagram Desktop app with target profile if provided."""
    username = target.strip().replace("@", "")
    
    try:
        # instagram://user?username=... for native PC apps
        if username:
            uri = f"instagram://user?username={username}"
            msg = f"Opening {username}'s profile on Instagram, Sir."
        else:
            uri = "instagram://"
            msg = "Launching the Instagram Desktop app, Sir."
            
        def _launch_insta():
            os.startfile(uri)
            logger.info(f"[INSTAGRAM] Launched URI: {uri}")

        threading.Thread(target=_launch_insta, daemon=True).start()
        
        return {
            "success": True,
            "status": "success",
            "message": msg
        }
    except Exception as e:
        # Fallback to browser if app is not installed or URI fails
        import webbrowser
        base_url = f"https://www.instagram.com/{username}" if username else "https://www.instagram.com"
        webbrowser.open(base_url)
        return {
            "success": True,
            "status": "success",
            "message": f"I couldn't launch the PC app, Sir. Opening Instagram in your browser instead."
        }
