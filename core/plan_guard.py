"""Validation boundary for AI-proposed actions.

AI text is a proposal, not an instruction to execute arbitrary tools. Only
registered actions and already loaded skills may pass; no permission or result
can be forged through extra fields.
"""
from __future__ import annotations

import json
from typing import Any, Iterable, Mapping

MAX_AI_STEPS = 3
MAX_TARGET = 4096
MAX_EXTRA_JSON = 4096
NO_TARGET_ACTIONS = frozenset({"system_check", "get_ui_tree", "self_reflect", "capture_screen"})
FORBIDDEN_EXTRA_KEYS = frozenset({
    "approved", "approval", "confirmed", "authorization",
    "skip_approval", "bypass_approval", "admin", "force_success",
})


def validate_ai_action_plan(
    steps: Any,
    registered_actions: Iterable[str],
    loaded_skills: Iterable[str] = (),
    allow_model_code: bool = False,
) -> dict[str, Any]:
    """Fail closed on malformed, unsupported or overlong AI plans."""
    if not isinstance(steps, list) or not steps:
        return {"error": "No structured AI actions were provided."}
    if len(steps) > MAX_AI_STEPS:
        return {"error": f"AI plan exceeds the {MAX_AI_STEPS}-action limit."}

    allowed = set(registered_actions) | {"open_dynamic"}
    skill_names = set(loaded_skills)
    validated = []
    seen = set()

    for index, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            return {"error": f"AI step {index} must be an object."}
        action = step.get("action")
        target = step.get("target", "")
        extra = step.get("extra", {})

        if not isinstance(action, str) or not action or action != action.strip():
            return {"error": f"AI step {index} has an invalid action name."}
        if action.startswith("skill:"):
            if action[6:] not in skill_names:
                return {"error": f"AI proposed an unavailable skill: {action[6:]}"}
        elif action not in allowed:
            return {"error": f"AI proposed an unsupported action: {action}"}

        if not isinstance(target, str) or "\x00" in target or len(target) > MAX_TARGET:
            return {"error": f"AI step {index} contains an invalid or oversized target."}
        if not target.strip() and action not in NO_TARGET_ACTIONS:
            return {"error": f"AI step {index} is missing a target for {action}."}
        if action == "execute_python" and not allow_model_code:
            return {"error": "AI-generated code execution is not enabled."}

        if not isinstance(extra, dict) or any(not isinstance(k, str) for k in extra):
            return {"error": f"AI step {index} has invalid extra parameters."}
        if FORBIDDEN_EXTRA_KEYS.intersection(k.lower() for k in extra):
            return {"error": f"AI step {index} tried to supply its own approval/result."}
        try:
            encoded = json.dumps(extra, sort_keys=True, allow_nan=False)
        except (ValueError, TypeError):
            return {"error": f"AI step {index} has non-JSON parameters."}
        if len(encoded) > MAX_EXTRA_JSON:
            return {"error": f"AI step {index} has oversized parameters."}

        key = (action, target, encoded)
        if key not in seen:
            validated.append({"action": action, "target": target, "extra": extra})
            seen.add(key)

    if not validated:
        return {"error": "AI plan contained no executable actions."}
    return {"steps": validated}
