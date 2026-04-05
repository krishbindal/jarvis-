from typing import Dict, Any
from google import genai
from utils.logger import get_logger
from config import GEMINI_API_KEY
from brain.providers.base import AIProvider, _safe_json_extract, _validate_steps

logger = get_logger(__name__)

class GeminiProvider(AIProvider):
    @property
    def name(self) -> str:
        return "Gemini"

    def is_available(self) -> bool:
        return bool(GEMINI_API_KEY)

    def generate_command(self, system_prompt: str, context: str, user_input: str) -> Dict[str, Any]:
        if not self.is_available():
            raise ValueError(f"Provider {self.name} is not available (Missing API Key).")
            
        full_prompt = f"{system_prompt}\n{context}\n\nUser: {user_input}\nAssistant:"
        
        logger.info(f"[AI] Attempting {self.name} (Cloud)...")
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=full_prompt
        )
        parsed = _safe_json_extract(response.text)
        if parsed.get("steps"):
            logger.info(f"[AI] {self.name} successful.")
            return _validate_steps(parsed)
        raise ValueError(f"{self.name} returned invalid step structure.")

    def query(self, system_msg: str, prompt: str) -> str:
        if not self.is_available():
            raise ValueError(f"Provider {self.name} is not available.")
            
        full_prompt = f"{system_msg}\n\nTask: {prompt}\n\nResponse:"
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=full_prompt
        )
        return response.text.strip()
