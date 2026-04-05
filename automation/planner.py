from __future__ import annotations

"""LLM-first automation planner with deterministic fallbacks."""

import json
import textwrap
from typing import Any, Dict, List

from brain.structured_output import parse_json_block
from core.command_parser import split_multi_step, normalize
from utils.logger import get_logger

from automation.plan import (
    ALLOWED_AUTOMATION_ACTIONS,
    AutomationPlan,
    AutomationStep,
    normalize_plan,
)

logger = get_logger(__name__)

PLAN_SYSTEM_MSG = (
    "You are Jarvis, a universal desktop automation planner. "
    "Break the command into minimal UI actions that work on any OS/app without site-specific logic. "
    "Allowed actions: open_app, open_url, search, click, type, scroll, download."
)

PLAN_INSTRUCTIONS = """
Return ONLY JSON:
{"goal": "...", "steps": [{"action":"open_app","target":"chrome","app":"chrome","tool":"open_app","reason":""}]}
Rules:
- 1-6 steps max, keep each atomic and generic (no app/site hardcoding).
- Prefer reusing the current app/browser from context; do not reopen if already active.
- search => describe what to search for; download => provide the URL if present.
- If the task is already complete, return an empty steps list with a short message.
"""


def _call_provider(prompt: str) -> Dict[str, Any]:
    """Attempt providers in order, returning parsed JSON dict or {}."""
    try:
        from brain.providers import registry
        providers = registry.get_providers()
    except Exception as exc:  # noqa: BLE001
        logger.debug("Planner provider registry unavailable: %s", exc)
        return {}

    for provider in providers:
        try:
            raw = provider.query(PLAN_SYSTEM_MSG, prompt)
            data = parse_json_block(raw)
            if data:
                data.setdefault("_raw", raw)
                data.setdefault("_provider", provider.name)
                return data
        except Exception as exc:  # noqa: BLE001
            logger.debug("Planner provider %s failed: %s", provider.name, exc)
    return {}


def _fallback_from_text(command: str) -> AutomationPlan:
    """Deterministic fallback using simple NLP splits."""
    normalized = normalize(command)
    parts = split_multi_step(command)
    steps: List[AutomationStep] = []

    last_app = ""
    for part in parts:
        if not part:
            continue
        lower = part.lower()
        if lower.startswith(("open ", "launch ", "start ")):
            target = part.split(" ", 1)[1].strip()
            steps.append(AutomationStep(action="open_app", target=target, app=target, tool="open_app"))
            last_app = target
        elif lower.startswith(("search ", "google ", "find ")):
            query = part.split(" ", 1)[1].strip()
            steps.append(AutomationStep(action="search", target=query, tool="search", app=last_app))
        elif lower.startswith(("go to ", "navigate ", "visit ")):
            target = part.split(" ", 1)[1].strip()
            steps.append(AutomationStep(action="open_url", target=target, tool="open_url", app=last_app))
        elif "download" in lower:
            query = lower.replace("download", "", 1).strip() or part.strip()
            steps.append(AutomationStep(action="download", target=query, tool="download"))
        elif "scroll" in lower:
            steps.append(AutomationStep(action="scroll", target="-800", tool="scroll"))
        elif "click" in lower:
            steps.append(AutomationStep(action="click", target="", tool="click"))
        elif "type" in lower:
            text = lower.replace("type", "", 1).strip() or part.strip()
            steps.append(AutomationStep(action="type", target=text, tool="type"))

    return AutomationPlan(goal=normalized or command, steps=steps, source="fallback")


def build_automation_plan(command: str, context: Dict[str, Any] | None = None) -> AutomationPlan:
    """
    Build an AutomationPlan from free-form text using AI with deterministic fallback.
    """
    if not command:
        return AutomationPlan(goal="", steps=[], source="empty")

    ctx = context or {}
    ctx_lite = {k: v for k, v in ctx.items() if k in ("current_app", "current_url", "last_action", "task_in_progress")}
    prompt = textwrap.dedent(
        f"""
        User command: {command}
        Context: {json.dumps(ctx_lite, default=str)}
        {PLAN_INSTRUCTIONS}
        """
    ).strip()

    data = _call_provider(prompt)
    if data:
        plan = normalize_plan(data, source=data.get("_provider", "llm"), raw=data.get("_raw", ""))
        # Filter to allowed actions only
        plan.steps = [s for s in plan.steps if s.action in ALLOWED_AUTOMATION_ACTIONS]
        if plan.steps:
            return plan

    # Fallback to deterministic splitter
    return _fallback_from_text(command)
