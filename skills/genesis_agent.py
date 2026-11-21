"""
JARVIS-X Phase 26: Genesis Mode (Self-Evolution Skill)
Allows Jarvis to biologically write, inject, and hot-reload entirely new skills on the fly.
"""

import os
import re
from typing import Any, Dict
from utils.logger import get_logger
from config import GROQ_API_KEY, ENABLE_SKILL_GENERATION
from skills.skill_staging import stage_skill_candidate
import sys
import importlib

logger = get_logger(__name__)

SKILL_NAME = "genesis"
SKILL_DESCRIPTION = "Genesis Mode: Automatically write and install new Jarvis skills on the fly"
SKILL_PATTERNS = [
    r"(?:learn|teach\s+yourself)\s+how\s+to\s+(.*)",
    r"(?:write|create)\s+a\s+(?:skill|plugin|module)\s+(?:to|for)\s+(.*)",
    r"add\s+a\s+feature\s+(?:to|for)\s+(.*)"
]

GENESIS_PROMPT = """You are 'Genesis Mode', the self-evolution module of the JARVIS-X copilot.
Your job is to generate a fully functioning Python skill module based on the user's request.
The user wants you to create a skill for: "{request}"

REQUIREMENTS FOR JARVIS-X SKILLS:
1. Must define `SKILL_NAME` (string, simple lowercase).
2. Must define `SKILL_DESCRIPTION` (string).
3. Must define `SKILL_PATTERNS` (list of regex strings to match user inputs related to the skill).
4. Must define `def execute(target: str, extra: Dict[str, Any] = None) -> Dict[str, Any]:
    """Generate a candidate without installing or importing model-written code."""
    if not ENABLE_SKILL_GENERATION:
        return {"success": False, "status": "disabled",
                "message": "Skill proposal generation is disabled. Set JARVIS_ENABLE_SKILL_GENERATION=1 to opt in."}
    if not GROQ_API_KEY:
        return {"success": False, "status": "config_required",
                "message": "A Groq API key is required to generate a candidate skill."}
    try:
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY, timeout=20.0)
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": GENESIS_PROMPT.format(request=target)}],
            temperature=0.2,
        )
        raw_code = (completion.choices[0].message.content or "").strip()
        if raw_code.startswith("```python"):
            raw_code = raw_code[9:]
        if raw_code.startswith("```"):
            raw_code = raw_code[3:]
        if raw_code.endswith("```"):
            raw_code = raw_code[:-3]
        raw_code = raw_code.strip()
        match = re.search(r'SKILL_NAME\\s*=\\s*["\\\']([^"\\\']+)["\\\']', raw_code)
        if not match:
            return {"success": False, "status": "error", "message": "Generated candidate has no SKILL_NAME."}
        return stage_skill_candidate(raw_code, match.group(1))
    except Exception as exc:
        logger.error("[GENESIS] Candidate generation failed: %s", exc)
        return {"success": False, "status": "error", "message": "Skill generation failed. Check local logs."}
