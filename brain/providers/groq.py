from typing import Dict, Any
from groq import Groq
from utils.logger import get_logger
from config import GROQ_API_KEY
from brain.providers.base import AIProvider, _safe_json_extract, _validate_steps
from brain.provider_config import PRIMARY_MODEL, FALLBACK_MODEL, FAST_MODEL, COMMAND_TEMP, QUERY_TEMP, NORMAL_TIMEOUT

logger = get_logger(__name__)

class GroqProvider(AIProvider):
    def __init__(self):
        self.models = [PRIMARY_MODEL, FALLBACK_MODEL]

    @property
    def name(self) -> str:
        return "Groq"

    def is_available(self) -> bool:
        return bool(GROQ_API_KEY)

    def generate_command(self, system_prompt: str, context: str, user_input: str) -> Dict[str, Any]:
        if not self.is_available():
            raise ValueError(f"Provider {self.name} is not available (Missing API Key).")

        for current_model in self.models:
            try:
                logger.info(f"[AI] Attempting {self.name} ({current_model})...")
                client = Groq(api_key=GROQ_API_KEY, timeout=NORMAL_TIMEOUT)
                completion = client.chat.completions.create(
                    model=current_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"{context}\n\nUser: {user_input}"},
                    ],
                    temperature=COMMAND_TEMP,
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
            
        client = Groq(api_key=GROQ_API_KEY, timeout=NORMAL_TIMEOUT)
        completion = client.chat.completions.create(
            model=PRIMARY_MODEL,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt},
            ],
            temperature=QUERY_TEMP,
        )
        return completion.choices[0].message.content.strip()
