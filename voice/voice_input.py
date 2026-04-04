from __future__ import annotations

"""Hybrid voice input using Groq Whisper (online) and Vosk (offline)."""

import json
import threading
import io
import wave
import requests
from pathlib import Path
from typing import Optional

import sounddevice as sd

import config
from utils.logger import get_logger
from utils.connectivity import is_online

logger = get_logger(__name__)

try:
    from vosk import KaldiRecognizer, Model
except Exception as exc:  # noqa: BLE001
    KaldiRecognizer = None
    Model = None
    logger.error("Vosk is not available: %s", exc)

COMMAND_KEYWORDS = [
    "open", "close", "download", "search",
    "play", "stop", "list", "create", "delete", "jarvis", "send", "kill",
    "text", "whatsapp", "message", "write", "start", "type"
]

NOISE_BLACKLIST = [
    "stavros", "s tavros", "stavros stavros", "stravos"
]

def clean_text(text: str) -> str:
    text_lower = text.lower().strip()
    
    # Drop known noise
    for noise in NOISE_BLACKLIST:
        if noise in text_lower:
            logger.debug("[VOICE] Filtered blacklisted noise: %s", noise)
            return ""

    words = text_lower.split()
    
    # Handle single letters (spelling)
    if len(words) > 3 and all(len(w) == 1 for w in words):
        return "".join(words)
        
    # Handle excessive repetition (typical of background noise transcription)
    if len(words) > 4:
        word_counts = {}
        for w in words:
            word_counts[w] = word_counts.get(w, 0) + 1
        if any(count > len(words) * 0.6 for count in word_counts.values()):
            logger.debug("[VOICE] Filtered repetitive noise: %s", text)
            return ""

    return text

class VoiceListener:
    def __init__(self, event_bus):
        self._event_bus = event_bus
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
        # Audio buffering for online transcription
        self._audio_buffer = io.BytesIO()
        self._buffer_lock = threading.Lock()
        
        # Ambient Wake Word Integration (Phase 20)
        self.ambient_mode = True
        self._listening_for_command = False
        
        if self._event_bus:
            self._event_bus.subscribe("jarvis_wake", self._on_jarvis_wake)
        
        # Load Vosk Model once
        self.model = None
        self.rec = None
        
        if Model is None:
            logger.error("Vosk dependency missing; cannot initialize VoiceListener.")
            return
            
        model_path = Path(config.VOICE_MODEL_PATH)
        if not model_path.exists():
            logger.error(f"Voice model not found at {model_path}")
            return
            
        try:
            self.model = Model(str(model_path))
            self.rec = KaldiRecognizer(self.model, 16000)
            logger.info("[VOICE] Hybrid engine initialized (Vosk + preparation for Groq).")
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to load Vosk model: %s", exc)

    def _transcribe_online(self, audio_data: bytes) -> Optional[str]:
        """Send audio to Groq Whisper for high-accuracy transcription."""
        if not config.GROQ_API_KEY:
            return None
            
        try:
            # Wrap in WAV format for API
            buffer = io.BytesIO()
            with wave.open(buffer, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2) # 16-bit
                wf.setframerate(16000)
                wf.writeframes(audio_data)
            
            buffer.seek(0)
            
            files = {
                'file': ('audio.wav', buffer, 'audio/wav')
            }
            data = {
                'model': 'whisper-large-v3',
                'response_format': 'json'
            }
            headers = {
                'Authorization': f'Bearer {config.GROQ_API_KEY}'
            }
            
            response = requests.post(
                'https://api.groq.com/openai/v1/audio/transcriptions',
                headers=headers,
                files=files,
                data=data,
                timeout=5
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('text', '').strip()
            else:
                logger.debug(f"[VOICE] Groq error: {response.status_code} {response.text}")
                return None
        except Exception as e:
            logger.debug(f"[VOICE] Online transcription failed: {e}")
            return None

    def _on_jarvis_wake(self, payload=None):
        """Phase 20: Wakes up the listener to process the next incoming command."""
        self._listening_for_command = True
        logger.info("[VOICE] Woke up! Listening for next command...")

    def _callback(self, indata, frames, time_info, status):
        """Audio callback from sounddevice."""
        if status:
            logger.debug("Audio status: %s", status)

        if self.ambient_mode and not self._listening_for_command:
            return  # Drop audio if we are in ambient mode and waiting for wake word

        audio_bytes = bytes(indata)
        
        # Add to buffer for online use
        with self._buffer_lock:
            self._audio_buffer.write(audio_bytes)

        if self.rec and self.rec.AcceptWaveform(audio_bytes):
            # End of utterance detected by Vosk
            result = json.loads(self.rec.Result())
            offline_text = result.get("text", "").strip()
            
            # Extract full buffer and reset
            with self._buffer_lock:
                full_audio = self._audio_buffer.getvalue()
                self._audio_buffer = io.BytesIO()

            def process_voice():
                final_text = offline_text
                
                # If online and text looks meaningful, try to polish with Groq
                if is_online() and config.GROQ_API_KEY and len(full_audio) > 16000: # at least 0.5s
                    online_text = self._transcribe_online(full_audio)
                    if online_text:
                        logger.info(f"[VOICE] Groq polished: '{online_text}' (Vosk said: '{offline_text}')")
                        final_text = online_text
                
                # Reset ambient listener so we wait for Wake Word again
                self._listening_for_command = False
                
                if final_text:
                    final_text = clean_text(final_text)
                    # Broad criteria to avoid noise triggering commands
                    if any(word in final_text.lower() for word in COMMAND_KEYWORDS) or len(final_text.split()) > 2:
                        logger.info("✅ Voice Command: %s", final_text)
                        self._event_bus.emit(
                            "command_received",
                            {"text": final_text, "source": "voice"}
                        )
                    else:
                        logger.debug("❌ Ignored partial speech: %s", final_text)
            
            # Process in background to not block the audio thread
            threading.Thread(target=process_voice, daemon=True).start()

    def _run(self):
        logger.info("Starting background hybrid voice listener.")
        try:
            with sd.RawInputStream(
                samplerate=16000,
                blocksize=4000,
                dtype='int16',
                channels=1,
                callback=self._callback
            ):
                while self._running:
                    sd.sleep(100)
        except Exception as exc:  # noqa: BLE001
            logger.error("Voice listener crashed: %s", exc)

    def start(self):
        if self._running or self.model is None or self.rec is None:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, name="voice-listener-thread", daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
