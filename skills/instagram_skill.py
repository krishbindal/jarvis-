"""Instagram launcher with validated usernames and truthful open results."""
from __future__ import annotations

import os
import re
import webbrowser
from typing import Any, Dict
from urllib.parse import quote

from utils.logger import get_logger

logger = get_logger(__name__)
SKILL_NAME = "instagram"
SKILL_DESCRIPTION = "Request Instagram app/profile launch without claiming profile loaded."
SKILL_PATTERNS = [
    r"(?:open\s+)?instagram\s*(?:for\s+)?(.*)?$",
    r"insta\s*(.*)?$",
]
_USERNAME = re.compile(r"[A-Za-z0-9._]{1,30}\Z")


def _parse_username(value: str) -> str | None:
    """Only native Instagram usernames; strip the user command prefix."""
    text = value.strip()
    match = re.fullmatch(
        r"(?:open\s+)?(?:instagram|insta)(?:\s+for)?(?:\s+(.+))?",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        text = (match.group(1) or "").strip()
    text = text.removeprefix("@")
    if not text:
        return ""
    if _USERNAME.fullmatch(text) is None:
        return None
    return text


def execute(target: str, extra: Dict[str, Any] = None) -> Dict[str, Any]:
    if not isinstance(target, str):
        return {"success": False, "status": "invalid_request", "message": "A text target is required."}

    username = _parse_username(target)
    if username is None:
        return {
            "success": False,
            "status": "invalid_username",
            "message": "Instagram usernames may contain only letters, digits, periods and underscores (up to 30 characters).",
        }

    uri = "instagram://" if not username else "instagram://user?username=" + quote(username, safe="")
    if hasattr(os, "startfile"):
        try:
            os.startfile(uri)
            return {
                "success": True,
                "status": "launch_requested",
                "message": "Instagram launch was handed to Windows. Page loading was not verified.",
            }
        except (OSError, ValueError):
            logger.info("[INSTAGRAM] Native launch unavailable; using browser fallback")

    url = "https://www.instagram.com/" + (quote(username, safe="") + "/" if username else "")
    try:
        accepted = webbrowser.open(url)
    except (OSError, ValueError):
        accepted = False
    if not accepted:
        return {
            "success": False,
            "status": "open_failed",
            "message": "Neither Instagram nor a browser confirmed accepting the launch request.",
        }
    return {
        "success": True,
        "status": "browser_open_requested",
        "message": "Browser accepted the Instagram URL. Profile loading was not verified.",
    }
