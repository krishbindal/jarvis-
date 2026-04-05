from typing import Dict, Any
from groq import Groq
from utils.logger import get_logger
from config import GROQ_API_KEY
from brain.providers.base import AIProvider, _safe_json_extract, _validate_steps

logger = get_logger(__name__)

class GroqProvider(AIProvider):
    def __init__(self):
        self.models = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]

    @property
    def name(self) -> str:
        return "Groq"

    def is_available(self) -> bool:
        return bool(GROQ_API_KEY)

    def generate_command(self, system_prompt: str, context: str, user_input: str) -> Dict[str, Any]:
        if not self.is_available():
            raise ValueError(f"Provider {self.name} is not available (Missing API Key).")

        full_prompt = f"{system_prompt}\n{context}\n\nUser: {user_input}\nAssistant:"
        
        for current_model in self.models:
            try:
                logger.info(f"[AI] Attempting {self.name} ({current_model})...")
                client = Groq(api_key=GROQ_API_KEY, timeout=8.0)
                completion = client.chat.completions.create(
                    model=current_model,
                    messages=[{"role": "user", "content": full_prompt}],
                    temperature=0.1,
                )
                output = completion.choices[0].message.content
                parsed = _safe_json_extract(output)
                if parsed.get("steps"):
                    logger.info(f"[AI] {self.name} ({current_model}) successful.")
                    return _validate_steps(parsed)
            except Exception as e:
                err_str = str(e).lower()
                if "429" in err_str or "rate_limit" in err_str:
                    logger.warning(f"[AI] {self.name} {current_model} hit rate limit (429).")
                    continue
                if "401" in err_str or "authentication" in err_str:
                    logger.error(f"[AI] {self.name} {current_model} auth failure (Invalid Key).")
                    break
                logger.warning(f"[AI] {self.name} {current_model} failed: {e}")
                break
                
        raise ValueError(f"{self.name} failed generating a valid command loop via all models.")

    def query(self, system_msg: str, prompt: str) -> str:
        if not self.is_available():
            raise ValueError(f"Provider {self.name} is not available.")
            
        full_prompt = f"{system_msg}\n\nTask: {prompt}\n\nResponse:"
        client = Groq(api_key=GROQ_API_KEY)
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": full_prompt}],
            temperature=0.3,
        )
        return completion.choices[0].message.content.strip()
