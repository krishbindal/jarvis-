"""
JARVIS-X Phase 26: The Forge (Skill Fabricator)
An out-of-the-box skill that allows Jarvis to write and register new skills for himself.
"""

import os
import re
from typing import Dict, Any
from utils.logger import get_logger
from brain.ai_engine import query_ai
from config import ENABLE_SKILL_GENERATION
from skills.skill_staging import stage_skill_candidate

logger = get_logger("THE_FORGE")

SKILL_NAME = "forge"
SKILL_DESCRIPTION = "Allows Jarvis to autonomously create and register new skills for himself."
SKILL_PATTERNS = [
    r"(?:create|fabricate|forge|make) (?:a )?new skill for (.+)",
    r"i (?:need|want) a skill to (.+)",
    r"build a skill that (.+)"
]

FORGE_PROMPT_TEMPLATE = """
You are the JARVIS-X Core Fabricator. Create a Python skill module for the following requirements:
{requirements}

The module MUST include exactly:
1. SKILL_NAME: a unique snake_case string.
2. SKILL_DESCRIPTION: a clear description.
3. SKILL_PATTERNS: a list of regex strings to trigger this skill.
4. execute(target: str, extra: Dict[str, Any]) -> Dict[str, Any]:
   - It should return a dict with {{"success": bool, "status": str, "message": str, "output": any}}.

Return ONLY the raw Python code. No markdown formatting, no backticks, no preamble.
"""

def execute(target: str, extra: Dict[str, Any] = None) -> Dict[str, Any]:
    """Generate an inert candidate for manual review; never auto-load it."""
    if not ENABLE_SKILL_GENERATION:
        return {"success": False, "status": "disabled",
                "message": "Skill proposal generation is disabled. Set JARVIS_ENABLE_SKILL_GENERATION=1 to opt in."}
    requirements = target or (extra or {}).get("requirements", "unspecified requirements")
    try:
        full_prompt = FORGE_PROMPT_TEMPLATE.format(requirements=requirements)
        raw = query_ai(full_prompt, system_msg="You are a Python developer drafting a skill for human review.")
        code = re.sub(r"```python\\n|```", "", raw).strip()
        name_match = re.search(r'SKILL_NAME\\s*=\\s*["\\\']([^"\\\']+)["\\\']', code)
        if not name_match:
            return {"success": False, "status": "error", "message": "Generated candidate has no SKILL_NAME."}
        return stage_skill_candidate(code, name_match.group(1))
    except Exception as exc:
        logger.error("[FORGE] Candidate generation failed: %s", exc)
        return {"success": False, "status": "error", "message": "Skill generation failed. Check local logs."}
