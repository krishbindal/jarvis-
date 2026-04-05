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
    data = parse_json_block(text)
    if not data:
        return {"steps": [], "type": "ai", "message": "AI parsing failed"}
    return data


def _validate_steps(data: Dict[str, Any]) -> Dict[str, Any]:
    steps = normalize_action_steps(data.get("steps"), max_steps=MAX_STEPS)
    message = clean_message(data.get("message"), default="Done.")
    return {"steps": steps, "type": "ai", "message": message}
