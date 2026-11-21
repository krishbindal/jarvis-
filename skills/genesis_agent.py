"""Genesis: generate review-only skill proposals, never hot-load AI-written code."""
from __future__ import annotations

from typing import Any, Dict
from config import GROQ_API_KEY, ENABLE_SKILL_GENERATION
from skills.skill_staging import extract_skill_name, stage_skill_candidate
from utils.logger import get_logger

logger = get_logger(__name__)
SKILL_NAME = "genesis"
SKILL_DESCRIPTION = "Draft a skill proposal for human review (not automatically installed)"
SKILL_PATTERNS = [
    r"(?:learn|teach\s+yourself)\s+how\s+to\s+(.*)",
    r"(?:write|create)\s+a\s+(?:skill|plugin|module)\s+(?:to|for)\s+(.*)",
    r"add\s+a\s+feature\s+(?:to|for)\s+(.*)",
]

GENESIS_PROMPT = """Draft a Python skill candidate for a human code review.
Task: {request}
Output ONLY a Python module, with constants SKILL_NAME, SKILL_DESCRIPTION,
SKILL_PATTERNS and a callable execute(target, extra=None).
Use a lowercase snake_case SKILL_NAME. This code will not run automatically.
"""


def execute(target: str, extra: Dict[str, Any] = None) -> Dict[str, Any]:
    if not ENABLE_SKILL_GENERATION:
        return {"success": False, "status": "disabled",
                "message": "Set JARVIS_ENABLE_SKILL_GENERATION=1 to opt into review-only skill proposals."}
    if not GROQ_API_KEY:
        return {"success": False, "status": "config_required",
                "message": "Set GROQ_API_KEY to generate skill proposals."}
    try:
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY, timeout=20.0)
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": GENESIS_PROMPT.format(request=target)}],
            temperature=0.2,
        )
        code = (completion.choices[0].message.content or "").strip()
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
        logger.error("[GENESIS] Skill proposal failed: %s", exc)
        return {"success": False, "status": "error", "message": "Skill proposal generation failed; see logs."}
