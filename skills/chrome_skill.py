from __future__ import annotations

"""Skill to open Chrome or a default browser."""

from typing import Any, Dict

from core.action_registry import execute_action
from utils.logger import get_logger

NAME = "chrome_launcher"
TRIGGERS = ["open chrome", "launch chrome", "start chrome", "chrome"]
DESCRIPTION = "Launches Chrome or falls back to opening a browser window."

logger = get_logger(__name__)


def run(command: str, context: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("[SKILL][CHROME] Triggered by command: %s", command)
    result = execute_action("open_app", "chrome", {})
    if result.get("success"):
        return result
    logger.warning("[SKILL][CHROME] open_app failed; falling back to open_url")
    return execute_action("open_url", "https://www.google.com", {})
