"""The Forge: skill candidate generator, without automatic code execution."""
from __future__ import annotations

from typing import Any, Dict
from brain.ai_engine import query_ai
from config import ENABLE_SKILL_GENERATION
from skills.skill_staging import extract_skill_name, stage_skill_candidate
from utils.logger import get_logger

logger = get_logger(__name__)
SKILL_NAME = "forge"
SKILL_DESCRIPTION = "Draft a skill for manual review, not installation"
SKILL_PATTERNS = [
    r"(?:create|fabricate|forge|make) (?:a )?new skill for (.+)",
    r"i (?:need|want) a skill to (.+)",
    r"build a skill that (.+)",
]

FORGE_PROMPT_TEMPLATE = """Draft a Python skill module for human review.
Requirements: {requirements}
Define SKILL_NAME (lowercase snake_case), SKILL_DESCRIPTION, SKILL_PATTERNS,
and execute(target, extra=None). Output only Python source.
This candidate must not be installed or executed automatically.
"""


def execute(target: str, extra: Dict[str, Any] = None) -> Dict[str, Any]:
    if not ENABLE_SKILL_GENERATION:
        return {"success": False, "status": "disabled",
                "message": "Set JARVIS_ENABLE_SKILL_GENERATION=1 to opt into review-only skill proposals."}
    requirements = target or (extra or {}).get("requirements", "unspecified requirements")
    try:
        raw = query_ai(
            FORGE_PROMPT_TEMPLATE.format(requirements=requirements),
            system_msg="Draft Python code for human review; return only a module.",
        )
        code = raw.strip()
        if code.startswith("```python"):
            code = code[len("```python"):]
        if code.startswith("```"):
            code = code[3:]
        if code.endswith("```"):
            code = code[:-3]
        code = code.strip()
        name = extract_skill_name(code)
        if name is None:
            return {"success": False, "status": "error", "message": "Generated candidate has no static SKILL_NAME."}
        return stage_skill_candidate(code, name)
    except Exception as exc:
        logger.error("[FORGE] Skill proposal failed: %s", exc)
        return {"success": False, "status": "error", "message": "Skill proposal generation failed; see logs."}
