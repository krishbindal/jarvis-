"""
JARVIS-X Phase 24: Code Buddy Mode

Skill: When VS Code is detected, offer code help.
Handles: "explain this code", "debug this", "what does this function do"
"""

from typing import Any, Dict
from utils.logger import get_logger

logger = get_logger(__name__)

SKILL_NAME = "code_buddy"
SKILL_DESCRIPTION = "Code assistance — 'explain this code', 'debug this error', 'what does this do'"
SKILL_PATTERNS = [
    r"explain\s+(?:this\s+)?(?:code|function|error|bug|snippet)",
    r"debug\s+(?:this|the)\s*(?:error|code|issue|problem)?",
    r"what\s+does\s+(?:this|that)\s+(?:code|function|method|class)\s+do",
    r"fix\s+(?:this|the)\s+(?:code|error|bug|issue)",
    r"help\s+me\s+(?:with|debug|fix)\s+(?:this|the)\s+(?:code|error)?",
    r"review\s+(?:this|my)\s+code",
]


def execute(target: str, extra: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Capture the screen and send to AI for code analysis.
    Uses the vision provider to see what's on screen.
    """
    try:
        from brain.vision_provider import get_vision_provider
        from brain.ai_engine import interpret_command

        provider = get_vision_provider()

        # Force a fresh screen capture
        logger.info("[CODE_BUDDY] Capturing screen for code analysis...")
        visual = provider.capture_now()

        # Build a code-specific prompt
        code_prompt = f"""The user is asking for code help: "{target}"
        
Current screen context: {visual}

Please analyze what you see and provide:
1. Identify the programming language
2. Explain what the code does (if visible)
3. If there's an error, explain the cause and suggest a fix
4. Be concise and actionable

Respond in JSON format:
{{"steps": [], "message": "Your helpful analysis here"}}"""

        result = interpret_command(code_prompt)
        message = result.get("message", "I've analyzed the code on your screen.")

        return {
            "success": True,
            "status": "success",
            "message": message,
            "output": "code_analysis",
        }

    except Exception as e:
        logger.error("[CODE_BUDDY] Analysis failed: %s", e)
        return {
            "success": False,
            "status": "error",
            "message": f"Code analysis failed: {e}",
        }
