from __future__ import annotations

"""Skill to download files or videos based on simple cues."""

import re
from typing import Any, Dict

from core.action_registry import execute_action
from utils.logger import get_logger

NAME = "downloader"
TRIGGERS = ["download", "save video", "grab video", "download video", "download file"]
DESCRIPTION = "Downloads files or videos using built-in executors."

logger = get_logger(__name__)


def _extract_url(command: str) -> str:
    match = re.search(r"(https?://\\S+)", command)
    return match.group(1) if match else ""


def run(command: str, context: Dict[str, Any]) -> Dict[str, Any]:
    url = _extract_url(command) or context.get("url", "")
    if not url:
        return {"success": False, "status": "error", "message": "No URL provided for download."}

    is_video = "video" in command.lower() or any(word in command.lower() for word in ["youtube", "yt"])
    action = "download_video" if is_video else "download_file"
    logger.info("[SKILL][DOWNLOAD] action=%s url=%s", action, url)
    return execute_action(action, url, {})
