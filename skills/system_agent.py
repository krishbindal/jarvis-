"""
JARVIS-X Phase 30: System Agent
Skill: Generates and executes Python code dynamically to fulfill system intents.
Handles: "convert", "download", "extract", "run", "do almost anything"
"""

from typing import Any, Dict

from utils.logger import get_logger
from config import GROQ_API_KEY, GEMINI_API_KEY, ALLOW_CODE_EXECUTION, ALLOW_MODEL_CODE_EXECUTION
from brain.provider_config import GEMINI_MODEL
from executor.python_runner import run_python_code

logger = get_logger(__name__)

_CODE_EXEC_DISABLED_MSG = (
    "Dynamic code execution is disabled for safety. "
    "Set JARVIS_ALLOW_CODE_EXECUTION=1 to enable it."
)

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
Do not install packages, modify permissions, contact third-party servers, or execute shell commands without a separate explicit user request.
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
                model=GEMINI_MODEL,
                contents=f"{SYSTEM_PROMPT}\n\nUser intent: {intent}"
            )
            return _clean_markdown(response.text)
        except Exception as e:
            logger.warning(f"Gemini failed for system agent: {e}")
            
    raise Exception("No AI provider available or all failed.")


def execute(target: str, extra: Dict[str, Any] = None) -> Dict[str, Any]:
    """Execute model-generated code only when both explicit opt-ins are enabled.

    This is not a security sandbox. Review generated code and run Jarvis with
    ordinary user permissions, never elevated permissions.
    """
    if not ALLOW_CODE_EXECUTION or not ALLOW_MODEL_CODE_EXECUTION:
        return {
            "success": False,
            "status": "disabled",
            "message": (
                "Generated scripts require both JARVIS_ALLOW_CODE_EXECUTION=1 and "
                "JARVIS_ALLOW_MODEL_CODE_EXECUTION=1. Model code runs with your "
                "normal filesystem/network permissions; manually review it first."
            ),
        }
    try:
        code = _generate_code(target)
        # Reuse one bounded, secret-filtering subprocess runner rather than
        # launching an unrestricted inherited-environment 'python' executable.
        return run_python_code(code)
    except Exception as exc:
        logger.error("[SYSTEM_AGENT] Failed: %s", exc)
        return {
            "success": False,
            "status": "error",
            "message": "System Agent failed; check the local logs.",
        }
