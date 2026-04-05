from __future__ import annotations

"""Helpers to enforce strict, minimal, and stable JSON outputs from LLMs."""

import json
from typing import Any, Dict, Iterable, List, Tuple

MAX_STEPS = 3


def _clean_str(value: Any) -> str:
    """Coerce any value into a trimmed single-line string."""
    if value is None:
        return ""
    if isinstance(value, str):
        value = value.replace("\n", " ").replace("\r", " ")
    return str(value).strip()


def parse_json_block(text: str) -> Dict[str, Any]:
    """
    Extract the first JSON object from free-form text.

    Returns an empty dict on failure to keep callers resilient.
    """
    try:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            return {}
        snippet = text[start : end + 1]
        return json.loads(snippet)
    except Exception:
        return {}


def clean_message(message: str, default: str = "Done.") -> str:
    """
    Normalize a message for TTS/UI: trimmed, single-line, length-limited.
    """
    msg = _clean_str(message)
    if not msg:
        return default
    if len(msg) > 160:
        msg = msg[:157].rstrip() + "..."
    return msg


def normalize_tool_steps(
    raw_steps: Any, allowed_tools: Iterable[str] | None = None, max_steps: int = MAX_STEPS
) -> List[Dict[str, str]]:
    """
    Normalize planner/tool steps into a predictable list.

    Keeps only allowed tools, removes duplicates, and caps length.
    """
    steps: List[Dict[str, str]] = []
    seen = set()
    if not isinstance(raw_steps, list):
        return steps

    allowed = set(allowed_tools) if allowed_tools else None
    for step in raw_steps:
        if not isinstance(step, dict):
            continue
        tool = _clean_str(step.get("tool") or step.get("action"))
        if not tool:
            continue
        if allowed and tool not in allowed:
            continue
        input_arg = _clean_str(
            step.get("input")
            or step.get("target")
            or step.get("arg")
            or step.get("value")
        )
        reason = _clean_str(step.get("reason") or step.get("why") or step.get("comment"))

        key = (tool, input_arg, reason)
        if key in seen:
            continue
        seen.add(key)
        steps.append({"tool": tool, "input": input_arg, "reason": reason})
        if len(steps) >= max_steps:
            break
    return steps


def normalize_action_steps(
    raw_steps: Any, allowed_actions: Iterable[str] | None = None, max_steps: int = MAX_STEPS
) -> List[Dict[str, Any]]:
    """
    Normalize AI action steps into dictionaries with action/target/extra.
    """
    steps: List[Dict[str, Any]] = []
    if not isinstance(raw_steps, list):
        return steps
    allowed = set(allowed_actions) if allowed_actions else None
    seen = set()

    for step in raw_steps:
        if not isinstance(step, dict):
            continue
        action = _clean_str(step.get("action"))
        if not action:
            continue
        if allowed and action not in allowed:
            continue
        target = _clean_str(step.get("target"))
        extra = step.get("extra") or {}
        key = (action, target, json.dumps(extra, sort_keys=True, default=str))
        if key in seen:
            continue
        seen.add(key)
        steps.append({"action": action, "target": target, "extra": extra})
        if len(steps) >= max_steps:
            break
    return steps


def parse_structured_response(
    raw_text: str,
    allowed_tools: Iterable[str] | None,
    default_message: str,
    max_steps: int = MAX_STEPS,
) -> Tuple[List[Dict[str, str]], str]:
    """
    Parse a planner-style response into normalized steps and a safe message.
    """
    data = parse_json_block(raw_text)
    steps = normalize_tool_steps(data.get("steps"), allowed_tools, max_steps=max_steps)
    message = clean_message(data.get("say") or data.get("message") or data.get("final"), default_message)
    return steps, message


def parse_ai_response(
    raw_text: str,
    allowed_actions: Iterable[str] | None = None,
    default_message: str = "Done.",
    max_steps: int = MAX_STEPS,
) -> Dict[str, Any]:
    """
    Parse a command interpreter JSON into validated steps/message payload.
    """
    data = parse_json_block(raw_text)
    steps = normalize_action_steps(data.get("steps"), allowed_actions, max_steps=max_steps)
    message = clean_message(data.get("message"), default_message)
    return {"steps": steps, "type": "ai", "message": message}
