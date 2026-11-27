from abc import ABC, abstractmethod
from typing import Dict, Any, List

from brain.structured_output import MAX_STEPS, clean_message, normalize_action_steps, parse_json_block

class AIProvider(ABC):
    """Abstract Base Class for AI Engine Providers."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the provider (e.g., 'Groq', 'Gemini', 'Ollama')."""
        pass

    @abstractmethod
    def generate_command(self, system_prompt: str, context: str, user_input: str) -> Dict[str, Any]:
        """
        Generate a command response containing 'steps' and a 'message'.
        Returns a dictionary validated for steps format.
        """
        pass

    @abstractmethod
    def query(self, system_msg: str, prompt: str) -> str:
        """
        General text-in, text-out query engine.
        """
        pass

def _safe_json_extract(text: str) -> Dict[str, Any]:
    """Malformed output is never rewritten as a valid no-action response."""
    return parse_json_block(text)


def _valid_command_response(data: Dict[str, Any]) -> bool:
    """Distinguish a valid empty plan from malformed AI JSON.

    Zero steps are legal only with an explicit explanation. A missing or
    non-list steps field, invalid individual step or oversized plan fails.
    Execution still passes through the independent action plan guard.
    """
    if not isinstance(data, dict):
        return False
    raw_steps = data.get("steps")
    if not isinstance(raw_steps, list) or len(raw_steps) > MAX_STEPS:
        return False
    if not raw_steps:
        msg = data.get("message")
        return isinstance(msg, str) and bool(msg.strip())
    return all(
        isinstance(step, dict)
        and isinstance(step.get("action"), str)
        and bool(step["action"].strip())
        and isinstance(step.get("target", ""), str)
        and isinstance(step.get("extra", {}), dict)
        for step in raw_steps
    )


def _validate_steps(data: Dict[str, Any]) -> Dict[str, Any]:
    steps = normalize_action_steps(data.get("steps"), max_steps=MAX_STEPS)
    message = clean_message(data.get("message"), default="Done.")
    return {"steps": steps, "type": "ai", "message": message}
