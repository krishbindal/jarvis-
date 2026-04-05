from __future__ import annotations

"""Hybrid voice input using Groq Whisper (online) and Vosk (offline)."""

import json
import threading
import io
import wave
import requests
import os
import time
from pathlib import Path
from typing import Optional

from utils.logger import get_logger
from utils.connectivity import is_online

logger = get_logger(__name__)

try:
    import sounddevice as sd
except Exception as exc:  # noqa: BLE001
    sd = None
    logger.error("sounddevice is not available: %s", exc)

import config

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
        self.ambient_mode = False # Always listen (Phase 32)
        self._listening_for_command = True
        
        self._is_jarvis_speaking = False
        self._last_wake_time = 0.0  # Cooldown tracker (Phase 32)
        self._last_audio_ts = time.time()
        self._last_speaking_ts = 0.0  # Echo suppression (Phase 32)
        self._silence_start_ts = time.time()
        self._max_listen_time = 7.0 # Total listening window before force-flush
        
        if self._event_bus:
            self._event_bus.subscribe("jarvis_wake", self._on_jarvis_wake)
            self._event_bus.subscribe("overlay_state", self._on_overlay_state)
            self._event_bus.subscribe("system_shutdown", self.stop)
        
        # Load Vosk Model once
        self.model = None
        self.rec = None
        
        if Model is None:
            logger.error("Vosk dependency missing; cannot initialize VoiceListener.")
            return
            
        try:
            # Find model folder
            voice_dir = os.path.dirname(os.path.abspath(__file__))
            model_path = os.path.join(voice_dir, "model")
            
            if not os.path.exists(model_path):
                # Fallback to absolute search or relative to root
                base_dir = os.path.dirname(voice_dir)
                model_alt = os.path.join(base_dir, "vosk-model-small-en-us-0.15")
                if os.path.exists(model_alt):
                    model_path = model_alt
                else:
                    logger.warning("[VOICE] Vosk model not found! Checked '%s' and '%s'", model_path, model_alt)
                    self.model = None
                    self.rec = None
                    return
            
            self.model = Model(str(model_path))
            self.rec = KaldiRecognizer(self.model, 16000)
            logger.info("[VOICE] Hybrid engine initialized (Vosk + preparation for Groq).")
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to load Vosk model: %s", exc)

        # Load OpenWakeWord directly into VoiceListener to avoid sounddevice conflicts
        self._oww_model = None
        try:
            import openwakeword
            from openwakeword.model import Model as OWWModel
            openwakeword.utils.download_models()
            self._oww_model = OWWModel(wakeword_models=["hey_jarvis"], inference_framework="onnx")
            logger.info("[VOICE] OpenWakeWord model loaded into VoiceListener.")
        except Exception as exc:
            logger.warning("[VOICE] OpenWakeWord failed to load: %s", exc)

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

    def _on_jarvis_wake(self, payload: Optional[dict] = None):
        """Handle wake-up event by preparing for command input."""
        payload = payload or {}
        now = time.time()
        
        # 2-second Cooldown: prevent self-triggering loops if echo cancellation fails
        if now - self._last_wake_time < 2.0:
            logger.debug("[VOICE] Wake event ignored (cooldown active)")
            return
            
        self._last_wake_time = now
        logger.info("[VOICE] JARVIS WAKE signal received. Starting command listener...")
        
        self._listening_for_command = True
        
        # Clear old audio buffer
        with self._buffer_lock:
            self._audio_buffer = io.BytesIO()
            
        # Acknowledge (skip if it was an internal relay to avoid loop)
        if payload.get("source") != "app_internal":
            from voice.tts_engine import speak
            speak("Yes, sir?")
        
    def _on_overlay_state(self, payload: dict):
        """Track if JARVIS is speaking to avoid hearing himself."""
        state = payload.get("state", "").lower()
        self._is_jarvis_speaking = (state == "speaking")
        if self._is_jarvis_speaking:
            self._last_speaking_ts = time.time()
        else:
            # Mark when he stopped for a short cooldown
            self._last_speaking_ts = time.time()

    def _callback(self, indata, frames, time_info, status):
        """Audio callback from sounddevice."""
        if status:
            logger.debug("Audio status: %s", status)

        # Echo Cancellation: Ignore audio while JARVIS is speaking + 500ms grace
        now = time.time()
        if self._is_jarvis_speaking or (now - self._last_speaking_ts < 0.5):
            return

        if self.ambient_mode and not self._listening_for_command:
            if self._oww_model:
                import numpy as np
                audio_array = np.frombuffer(bytes(indata), dtype=np.int16)
                try:
                    prediction = self._oww_model.predict(audio_array)
                    for model_name, score in prediction.items():
                        if score > 0.5:
                            logger.info("[VOICE] OpenWakeWord detected '%s' (score=%.3f)", model_name, score)
                            self._oww_model.reset()
                            
                            # Fire wake word sequence
                            if self._event_bus:
                                self._event_bus.emit("interrupt_tts")
                                self._event_bus.emit("jarvis_wake")
                                self._event_bus.emit("overlay_state", {"state": "listening", "text": "Hey Jarvis!"})
                            
                            # Play activation sound
                            try:
                                from utils.notifications import notify
                                notify("🎤 Jarvis Activated", "Listening for your command...")
                            except Exception:
                                pass
                            return
                except Exception as e:
                    logger.error("[Voice] OpenWakeWord predict error: %s", e)

            # Drop audio if wake word hasn't triggered
            return

        audio_bytes = bytes(indata)
        self._last_audio_ts = time.time()
        
        # Add to buffer for online use
        with self._buffer_lock:
            self._audio_buffer.write(audio_bytes)

        # Force flush if listening for too long (Phase 32)
        force_flush = False
        if time.time() - self._silence_start_ts > self._max_listen_time:
            logger.debug("[VOICE] Maximum phrase duration reached. Forcing transcription.")
            force_flush = True

        if self.rec and (self.rec.AcceptWaveform(audio_bytes) or force_flush):
            # End of utterance detected by Vosk
            result = json.loads(self.rec.Result())
            offline_text = result.get("text", "").strip()
            
            # Extract full buffer and reset
            with self._buffer_lock:
                full_audio = self._audio_buffer.getvalue()
                self._audio_buffer = io.BytesIO()

            def process_voice():
                final_text = offline_text
                
                # Noise Gate: Only polish if we have some offline text or substantial audio
                if is_online() and config.GROQ_API_KEY:
                    # Skip polishing if Vosk heard nothing and we are just idling in ambient mode
                    if not offline_text and len(full_audio) < 32000: # Less than 1 second of audio
                         return

                    online_text = self._transcribe_online(full_audio)
                    if online_text and len(online_text.strip()) > 2:
                        logger.info(f"[VOICE] Groq polished: '{online_text}' (Vosk said: '{offline_text}')")
                        final_text = online_text
                
                # Keep listening permanently in "Always Listening" mode
                if self.ambient_mode:
                    self._listening_for_command = False
                
                # Reset phrase time tracker
                self._silence_start_ts = time.time()
                
                if self._event_bus:
                    self._event_bus.emit("command_complete")
                
                if final_text:
                    final_text = clean_text(final_text)
                    if final_text.strip().lower() in ("stop", "cancel", "abort", "quiet"):
                        logger.info("[VOICE] Stop word detected, interrupting speech/streams.")
                        self._event_bus.emit("interrupt_tts")
                        self._event_bus.emit("command_progress", {"stage": "interrupt", "text": "User requested stop"})
                        return
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
        logger.info("[VOICE] Starting background hybrid voice listener.")
        try:
            with sd.RawInputStream(
                samplerate=16000,
                dtype='int16',
                channels=1,
                blocksize=1280, # Match OpenWakeWord's preference
                callback=self._callback
            ):
                while self._running:
                    sd.sleep(100)
        except Exception as exc:  # noqa: BLE001
            logger.error("[VOICE] Listener crashed or could not access microphone: %s", exc)
            # Try to list devices for the user in the logs
            try:
                devices = sd.query_devices()
                logger.info("[VOICE] Available audio devices:\n%s", devices)
            except Exception:
                pass

    def start(self):
        if self._running or self.model is None or self.rec is None:
            return
        if sd is None:
            logger.warning("[VOICE] sounddevice missing; voice listener disabled.")
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, name="voice-listener-thread", daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
