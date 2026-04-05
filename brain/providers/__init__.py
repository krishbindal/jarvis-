from typing import List, Optional
from brain.providers.base import AIProvider
from brain.providers.gemini import GeminiProvider
from brain.providers.groq import GroqProvider
from brain.providers.ollama import OllamaProvider

class ProviderRegistry:
    """Manages the fallback hierarchy of AI Providers."""
    def __init__(self):
        # The order here defines the fallback priority
        # Groq (Ultra-fast cloud) -> Gemini (Free cloud fallback) -> Ollama (Local last resort)
        self.providers: List[AIProvider] = [
            GroqProvider(),
            GeminiProvider(),
            OllamaProvider()
        ]

    def get_providers(self) -> List[AIProvider]:
        """Return the ordered list of providers."""
        return self.providers

registry = ProviderRegistry()
