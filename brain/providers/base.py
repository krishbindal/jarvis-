from abc import ABC, abstractmethod
from typing import Dict, Any, List

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
    import json
    try:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            raise ValueError("No JSON object found")
        snippet = text[start : end + 1]
        return json.loads(snippet)
    except Exception:
        return {"steps": [], "type": "ai", "message": "AI parsing failed"}


def _validate_steps(data: Dict[str, Any]) -> Dict[str, Any]:
    steps = data.get("steps", [])
    message = data.get("message") or ""
    if not isinstance(steps, list):
        return {"steps": [], "type": "ai", "message": message or "AI parsing failed"}
    cleaned = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        action = step.get("action") or "unknown"
        target = step.get("target") or ""
        extra = step.get("extra") or {}
        cleaned.append({"action": action, "target": target, "extra": extra})
    return {"steps": cleaned, "type": "ai", "message": message}
