from typing import Dict, Any
import requests
from utils.logger import get_logger
from config import MODEL_NAME
from brain.providers.base import AIProvider, _safe_json_extract, _validate_steps

OLLAMA_URL = "http://localhost:11434/api/generate"
logger = get_logger(__name__)

class OllamaProvider(AIProvider):
    @property
    def name(self) -> str:
        return "Ollama"

    def is_available(self) -> bool:
        # Simplistic check if the URL is somewhat valid and local configuration allows it
        # Real verification would hit /api/tags
        return True

    def generate_command(self, system_prompt: str, context: str, user_input: str) -> Dict[str, Any]:
        full_prompt = f"{system_prompt}\n{context}\n\nUser: {user_input}\nAssistant:"
        logger.info(f"[AI] Attempting {self.name} ({MODEL_NAME} - High Resource Usage)...")
        payload = {"model": MODEL_NAME, "prompt": full_prompt, "stream": False}
        
        try:
            resp = requests.post(OLLAMA_URL, json=payload, timeout=8)
            resp.raise_for_status()
            output = resp.json().get("response", "")
            parsed = _safe_json_extract(output)
            if parsed.get("steps"):
                logger.info(f"[AI] {self.name} ({MODEL_NAME}) successful.")
                return _validate_steps(parsed)
            raise ValueError(f"{self.name} output did not contain valid steps.")
        except Exception as e:
            logger.warning(f"[AI] {self.name} failed (Local): {e}")
            raise

    def query(self, system_msg: str, prompt: str) -> str:
        full_prompt = f"{system_msg}\n\nTask: {prompt}\n\nResponse:"
        payload = {"model": MODEL_NAME, "prompt": full_prompt, "stream": False}
        resp = requests.post(OLLAMA_URL, json=payload, timeout=10)
        if resp.status_code == 200:
            return resp.json().get("response", "").strip()
        raise ValueError(f"{self.name} local request failed.")
