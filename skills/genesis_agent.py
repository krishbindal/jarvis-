"""
JARVIS-X Phase 26: Genesis Mode (Self-Evolution Skill)
Allows Jarvis to biologically write, inject, and hot-reload entirely new skills on the fly.
"""

import os
import re
from typing import Any, Dict
from utils.logger import get_logger
from config import GROQ_API_KEY
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
4. Must define `def execute(target: str, extra: Dict[str, Any] = None) -> Dict[str, Any]:`
5. The `execute` function must return a dictionary: {{"success": bool, "status": "success"|"error", "message": "What to say", "output": Any}}

Output ONLY the raw Python code. No markdown code blocks like ```python, no explanations. Just python code. Use absolute imports.
Make the code flawless. If it needs external standard libraries like requests, json, os, urllib, use them.
"""

def execute(target: str, extra: Dict[str, Any] = None) -> Dict[str, Any]:
    """Generates a new python skill using Groq, saves it, and hot reloads."""
    if not GROQ_API_KEY:
        return {"success": False, "status": "error", "message": "Genesis mode requires GROQ_API_KEY to write high-speed code."}

    logger.info(f"[GENESIS] Initiating evolution protocol for: {target}")
    
    try:
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": GENESIS_PROMPT.format(request=target)}],
            temperature=0.2,
        )
        
        raw_code = completion.choices[0].message.content.strip()
        
        # Remove potential markdown
        if raw_code.startswith("```python"):
            raw_code = raw_code[9:]
        if raw_code.startswith("```"):
            raw_code = raw_code[3:]
        if raw_code.endswith("```"):
            raw_code = raw_code[:-3]
            
        raw_code = raw_code.strip()
        
        # Extract the SKILL_NAME to use as filename
        match = re.search(r'SKILL_NAME\s*=\s*["\']([^"\']+)["\']', raw_code)
        if not match:
            return {"success": False, "status": "error", "message": "Generated skill was invalid. No SKILL_NAME found."}
            
        skill_name = match.group(1).replace(" ", "_").lower()
        file_path = os.path.join(os.path.dirname(__file__), f"{skill_name}_agent.py")
        
        # Save the skill
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(raw_code)
            
        logger.info(f"[GENESIS] Skill saved to {file_path}")
        
        # Force Hot-Reload
        import skills
        # Invalidate module caches
        importlib.invalidate_caches()
        skills.discover_skills()
        
        return {
            "success": True,
            "status": "success",
            "message": f"Genesis complete. I have successfully written and learned the {skill_name} skill. It is now active.",
            "output": raw_code
        }
        
    except Exception as e:
        logger.error(f"[GENESIS] Evolution failed: {e}")
        return {"success": False, "status": "error", "message": f"Genesis protocol failed: {e}"}
