from __future__ import annotations

"""Deterministic-first automation planner with LLM enhancement."""

import json
import re
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
- CRITICAL: If the task is coding, calculations, system queries, or reflection, return an empty steps list.
"""

# Commands that are clearly conversational — should bypass automation entirely
_CONVERSATIONAL_PREFIXES = (
    "what ", "who ", "why ", "how ", "when ", "where ",
    "tell me", "explain", "describe", "can you", "do you",
    "remember", "what was", "what's", "what is", "who is",
    "how do", "how to", "should i", "could you", "would you",
    "is there", "are there", "define ", "meaning of",
    "thank", "thanks", "hello", "hey", "hi ", "good ",
)

# Strict prefix-based actions — only when command clearly starts with these
_ACTION_PREFIXES = {
    ("open ", "launch ", "start "): "open_app",
    ("search ", "google ",): "search",
    ("go to ", "navigate to ", "visit "): "open_url",
}


def _is_conversational(command: str) -> bool:
    """Check if a command is conversational and should bypass automation."""
    lower = command.lower().strip()
    if lower.startswith(_CONVERSATIONAL_PREFIXES):
        return True
    # Single-word or very short inputs are usually conversational
    if len(lower.split()) <= 2 and not lower.startswith(("open ", "launch ", "start ", "search ")):
        return True
    return False


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
    """Deterministic fallback using strict prefix matching."""
    normalized = normalize(command)
    parts = split_multi_step(command)
    steps: List[AutomationStep] = []

    last_app = ""
    for part in parts:
        if not part:
            continue
        lower = part.lower().strip()

        matched = False
        for prefixes, action in _ACTION_PREFIXES.items():
            if lower.startswith(prefixes):
                # Extract target after the prefix
                for p in prefixes:
                    if lower.startswith(p):
                        target = part[len(p):].strip()
                        break
                if action == "open_app":
                    steps.append(AutomationStep(action="open_app", target=target, app=target, tool="open_app"))
                    last_app = target
                elif action == "search":
                    steps.append(AutomationStep(action="search", target=target, tool="search", app=last_app))
                elif action == "open_url":
                    steps.append(AutomationStep(action="open_url", target=target, tool="open_url", app=last_app))
                matched = True
                break

        if matched:
            continue

        # Only match "download" as a prefix, not substring
        if lower.startswith("download "):
            query = lower.replace("download", "", 1).strip() or part.strip()
            steps.append(AutomationStep(action="download", target=query, tool="download"))

    return AutomationPlan(goal=normalized or command, steps=steps, source="fallback")


def build_automation_plan(command: str, context: Dict[str, Any] | None = None) -> AutomationPlan:
    """
    Build an AutomationPlan — deterministic first, LLM for complex cases only.
    Conversational commands are rejected immediately so the AI engine handles them.
    """
    if not command:
        return AutomationPlan(goal="", steps=[], source="empty")

    # Conversational bypass — let the AI engine handle these with full personality
    if _is_conversational(command):
        logger.debug("[PLANNER] Conversational bypass: '%s'", command[:60])
        return AutomationPlan(goal=command, steps=[], source="conversational_bypass")

    # Try deterministic matching first (instant, no LLM latency)
    deterministic = _fallback_from_text(command)
    if deterministic.steps:
        logger.debug("[PLANNER] Deterministic match: %s", deterministic.summary())
        return deterministic

    # Fall back to LLM for complex/ambiguous commands
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
        plan.steps = [s for s in plan.steps if s.action in ALLOWED_AUTOMATION_ACTIONS]
        if plan.steps:
            return plan

    # Nothing matched — return empty plan so command falls through to AI engine
    return AutomationPlan(goal=command, steps=[], source="no_match")
