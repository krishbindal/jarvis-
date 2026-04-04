"""
JARVIS-X Phase 30: System Agent
Skill: Generates and executes Python code dynamically to fulfill system intents.
Handles: "convert", "download", "extract", "run", "do almost anything"
"""

import os
import subprocess
import tempfile
from typing import Any, Dict

from utils.logger import get_logger
from config import GROQ_API_KEY, GEMINI_API_KEY

logger = get_logger(__name__)

SKILL_NAME = "system_agent"
SKILL_DESCRIPTION = "Agentic system control — download files, convert formats, execute scripts"

# Patterns to match any explicit action verbs related to OS tasks
SKILL_PATTERNS = [
    r"^(?:convert|download|extract|rename|compress|unzip)\s+(.+)",
    r"^(?:run|execute|fetch|grab|system|computer)\s+(.+)",
]

SYSTEM_PROMPT = """You are an elite Python expert acting as the operating system controller.
You will receive an intent. You MUST output ONLY valid python code to accomplish the intent.
Do not use markdown blocks like ```python. Just output raw python code. DO NOT ADD COMMENTARY.
Use the standard library where possible (e.g. urllib, os, shutil, subprocess, pathlib).
If you need external libraries (like Pillow, yt-dlp, requests), you can try to install them via `subprocess.call(['pip', 'install', '--quiet', '...'])` at the very top of your script.
Your code will be executed on a Windows 11 machine. Ensure paths are joined properly (raw strings for windows paths).
Always print the outcome or final file paths to stdout so the user knows what happened.
"""

def _clean_markdown(text: str) -> str:
    """Strip markdown code blocks if the LLM provided them."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"): lines = lines[1:]
        if lines[-1].startswith("```"): lines = lines[:-1]
        return "\n".join(lines)
    return text

def _generate_code(intent: str) -> str:
    """Generate Python code using Groq or Gemini."""
    # 1. Try Groq (Fastest)
    if GROQ_API_KEY:
        try:
            from groq import Groq
            client = Groq(api_key=GROQ_API_KEY)
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Write a Python script to do this: {intent}"}
                ],
                temperature=0.1,
            )
            return _clean_markdown(completion.choices[0].message.content)
        except Exception as e:
            logger.warning(f"Groq failed for system agent: {e}")
            
    # 2. Try Gemini
    if GEMINI_API_KEY:
        try:
            from google import genai
            client = genai.Client(api_key=GEMINI_API_KEY)
            response = client.models.generate_content(
                model='gemini-1.5-flash',
                contents=f"{SYSTEM_PROMPT}\n\nUser intent: {intent}"
            )
            return _clean_markdown(response.text)
        except Exception as e:
            logger.warning(f"Gemini failed for system agent: {e}")
            
    raise Exception("No AI provider available or all failed.")


def execute(target: str, extra: Dict[str, Any] = None) -> Dict[str, Any]:
    """Dynamically generate and execute a script to fulfill the intent."""
    logger.info(f"[SYSTEM_AGENT] Goal: {target}")
    try:
        # Generate the Python script
        code = _generate_code(target)
        logger.debug(f"[SYSTEM_AGENT] Generated Code:\n{code}")
        
        # Write to a temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(code)
            tmp_path = f.name
            
        logger.info(f"[SYSTEM_AGENT] Executing dynamic script...")
        
        # Execute the script
        result = subprocess.run(["python", tmp_path], capture_output=True, text=True, timeout=120)
        
        # Cleanup
        try:
            os.remove(tmp_path)
        except Exception:
            pass
            
        if result.returncode == 0:
            msg = result.stdout.strip() if result.stdout else "Operation completed successfully."
            logger.info(f"[SYSTEM_AGENT] Success: {msg[:100]}")
            return {
                "success": True,
                "status": "success",
                "message": msg[:200],  # Give Jarvis a short response to say
                "output": msg
            }
        else:
            err = result.stderr.strip()
            logger.error(f"[SYSTEM_AGENT] Script Error:\n{err}")
            return {
                "success": False,
                "status": "error",
                "message": f"I hit an error: {err[:150]}"
            }
            
    except Exception as e:
        logger.error(f"[SYSTEM_AGENT] Failed: {e}")
        return {
            "success": False,
            "status": "error",
            "message": f"System Agent error: {str(e)[:150]}"
        }
