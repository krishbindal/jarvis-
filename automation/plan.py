from __future__ import annotations

"""Shared data structures for universal automation plans."""

from dataclasses import dataclass, field
from typing import Any, Dict, List

ALLOWED_AUTOMATION_ACTIONS = {
    "open_app",
    "open_url",
    "search",
    "click",
    "type",
    "scroll",
    "download",
}


@dataclass
class AutomationStep:
    """A single planned automation action."""

    action: str
    target: str = ""
    app: str = ""
    tool: str = ""
    reason: str = ""
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a serializable dict for logging/telemetry."""
        return {
            "action": self.action,
            "target": self.target,
            "app": self.app,
            "tool": self.tool,
            "reason": self.reason,
            "meta": self.meta,
        }


@dataclass
class AutomationPlan:
    """Structured representation of a user intent and actionable steps."""

    goal: str
    steps: List[AutomationStep] = field(default_factory=list)
    source: str = "fallback"
    raw: str = ""
    message: str = ""

    def is_actionable(self) -> bool:
        return bool(self.steps)

    def summary(self) -> str:
        return f"{len(self.steps)} step(s) from {self.source}"


def _clean_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def normalize_plan(data: Dict[str, Any], source: str = "llm", raw: str = "") -> AutomationPlan:
    """
    Normalize arbitrary AI output into an AutomationPlan.

    Keeps only allowed actions, drops duplicates, and normalizes whitespace.
    """
    goal = _clean_str(data.get("goal") or data.get("intent") or data.get("task") or "")
    message = _clean_str(data.get("message", ""))
    seen = set()
    steps: List[AutomationStep] = []

    for step in data.get("steps", []) or []:
        if not isinstance(step, dict):
            continue
        action = _clean_str(step.get("action") or step.get("tool"))
        if not action or action not in ALLOWED_AUTOMATION_ACTIONS:
            continue
        target = _clean_str(step.get("target") or step.get("input") or step.get("value"))
        app = _clean_str(step.get("app"))
        tool = _clean_str(step.get("tool")) or action
        reason = _clean_str(step.get("reason") or step.get("why"))
        meta = step.get("meta") or {}

        key = (action, target, app, tool, reason)
        if key in seen:
            continue
        seen.add(key)
        steps.append(AutomationStep(action=action, target=target, app=app, tool=tool, reason=reason, meta=meta))

    return AutomationPlan(goal=goal or "", steps=steps, source=source, raw=raw, message=message)
