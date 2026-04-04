"""
JARVIS-X Phase 26: The Forge (Skill Fabricator)
An out-of-the-box skill that allows Jarvis to write and register new skills for himself.
"""

import os
import re
from typing import Dict, Any
from utils.logger import get_logger
from brain.ai_engine import query_ai

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

def execute(target: str, extra: Dict[str, Any]) -> Dict[str, Any]:
    """Fabricate a new skill based on the target requirements."""
    requirements = target or extra.get("requirements", "unspecified requirements")
    logger.info("[FORGE] Initiating fabrication for: %s", requirements)
    
    full_prompt = FORGE_PROMPT_TEMPLATE.format(requirements=requirements)
    
    try:
        # 1. Generate the code
        skill_code = query_ai(full_prompt, system_msg="You are an expert Python developer specialized in Jarvis-X skills.")
        
        # Clean up any accidental markdown backticks if AI ignored instructions
        skill_code = re.sub(r"```python\n|```", "", skill_code).strip()

        # 2. Extract skill name for filename
        name_match = re.search(r'SKILL_NAME\s*=\s*["\']([^"\']+)["\']', skill_code)
        if not name_match:
            return {"success": False, "status": "error", "message": "Fabrication failed: AI did not provide a SKILL_NAME."}
        
        skill_filename = f"{name_match.group(1)}.py"
        skills_dir = os.path.dirname(__file__)
        file_path = os.path.join(skills_dir, skill_filename)

        # 3. Write the file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(skill_code)
        
        # 4. Re-discover skills
        from skills import discover_skills
        discover_skills()
        
        return {
            "success": True, 
            "status": "success", 
            "message": f"Sir, I have successfully forged the '{skill_filename}' skill. Internal systems have been re-indexed to incorporate the new capability.",
            "output": {"filename": skill_filename, "path": file_path}
        }

    except Exception as e:
        logger.error("[FORGE] Fabrication failed: %s", e)
        return {"success": False, "status": "error", "message": f"Sir, my fabrication cycle failed: {e}"}
