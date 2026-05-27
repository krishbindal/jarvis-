from typing import Dict, Any
import time
import requests
from utils.logger import get_logger
from config import MODEL_NAME
from brain.providers.base import AIProvider, _safe_json_extract, _validate_steps
from brain.provider_config import NORMAL_TIMEOUT

OLLAMA_BASE = "http://localhost:11434"
OLLAMA_URL = f"{OLLAMA_BASE}/api/chat"
logger = get_logger(__name__)

# Cached availability check
_available_cache: dict = {"value": None, "ts": 0.0}
_CACHE_TTL = 30.0  # seconds


class OllamaProvider(AIProvider):
    @property
    def name(self) -> str:
        return "Ollama"

    def is_available(self) -> bool:
        now = time.monotonic()
        if _available_cache["value"] is not None and (now - _available_cache["ts"]) < _CACHE_TTL:
            return _available_cache["value"]
        try:
            resp = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=1.5)
            ok = resp.status_code == 200
        except Exception:
            ok = False
        _available_cache["value"] = ok
        _available_cache["ts"] = now
        if not ok:
            logger.debug("[AI] Ollama is not reachable — skipping.")
        return ok

    def generate_command(self, system_prompt: str, context: str, user_input: str) -> Dict[str, Any]:
        if not self.is_available():
            raise ValueError(f"Provider {self.name} is not reachable.")

        logger.info(f"[AI] Attempting {self.name} ({MODEL_NAME} - High Resource Usage)...")
        payload = {
            "model": MODEL_NAME,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"{context}\n\nUser: {user_input}"},
            ],
            "stream": False,
        }
        
        try:
            resp = requests.post(OLLAMA_URL, json=payload, timeout=NORMAL_TIMEOUT)
            resp.raise_for_status()
            output = resp.json().get("message", {}).get("content", "")
            parsed = _safe_json_extract(output)
            if parsed.get("steps"):
                logger.info(f"[AI] {self.name} ({MODEL_NAME}) successful.")
                return _validate_steps(parsed)
            raise ValueError(f"{self.name} output did not contain valid steps.")
        except Exception as e:
            logger.warning(f"[AI] {self.name} failed (Local): {e}")
            raise

    def query(self, system_msg: str, prompt: str) -> str:
        if not self.is_available():
            raise ValueError(f"Provider {self.name} is not reachable.")

        payload = {
            "model": MODEL_NAME,
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
        }
        resp = requests.post(OLLAMA_URL, json=payload, timeout=NORMAL_TIMEOUT + 2)
        if resp.status_code == 200:
            return resp.json().get("message", {}).get("content", "").strip()
        raise ValueError(f"{self.name} local request failed.")
