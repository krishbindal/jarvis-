import asyncio
import edge_tts
import pygame
import tempfile
import os
import threading
from utils.logger import get_logger

logger = get_logger(__name__)

# Premium voice selection (Indian English or UK Male for Jarvis feel)
# Options: en-IN-NeerjaNeural, en-IN-PrabhatNeural, en-GB-RyanNeural
VOICE = "en-GB-RyanNeural" 

class TTSEngine:
    """Asynchronous TTS engine using Edge-TTS and Pygame."""

    def __init__(self):
        pygame.mixer.init()
        self._lock = threading.Lock()
        self._is_speaking = False

    async def _amain(self, text: str, output_file: str) -> None:
        communicate = edge_tts.Communicate(text, VOICE)
        await communicate.save(output_file)

    def speak(self, text: str):
        """Thread-safe call to speak text."""
        if not text:
            return
        
        def _speak_thread():
            with self._lock:
                try:
                    # 1. Generate Audio
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
                        tmp_path = tmp.name
                    
                    asyncio.run(self._amain(text, tmp_path))
                    
                    # 2. Play Audio
                    pygame.mixer.music.load(tmp_path)
                    pygame.mixer.music.play()
                    
                    while pygame.mixer.music.get_busy():
                        pygame.time.Clock().tick(10)
                        
                    # 3. Cleanup
                    pygame.mixer.music.unload()
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
                        
                except Exception as e:
                    logger.error(f"TTS Synthesis failed: {e}")

        threading.Thread(target=_speak_thread, daemon=True).start()

# Global instance
_engine = None

def speak(text: str):
    global _engine
    if _engine is None:
        _engine = TTSEngine()
    _engine.speak(text)
