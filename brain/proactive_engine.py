"""
JARVIS-X Phase 17: Proactive Engine

This engine runs in the background, consuming data from VisionProvider,
SystemMonitor, and the EventBus. It decides whether to proactively
notify the user (e.g., "High CPU usage", or "Can I help with that code?").
"""

import hashlib
import threading
import time
from typing import Optional

from utils.logger import get_logger
from utils.system_context import get_system_stats
from brain.vision_provider import get_visual_context
from brain.ai_engine import query_ai

logger = get_logger("jarvis.proactive")

class ProactiveEngine:
    def __init__(self, event_bus, interval_seconds: int = 60):
        self._interval = interval_seconds
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._bus = event_bus
        self._last_context_hash = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="proactive-engine")
        self._thread.start()
        logger.info("[PROACTIVE] Engine started.")

    def stop(self):
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        logger.info("[PROACTIVE] Engine stopped.")

    def _loop(self):
        time.sleep(15)  # Initial delay
        while self._running:
            try:
                self._analyze_context()
            except Exception as e:
                logger.error(f"[PROACTIVE] Analysis error: {e}")
            
            time.sleep(self._interval)

    def _analyze_context(self):
        stats = get_system_stats()
        vision_ctx = get_visual_context()

        # Build context
        context = f"CPU: {stats['cpu_percent']}%, RAM: {stats['memory_percent']}%"
        if vision_ctx and vision_ctx != "No visual context yet.":
            context += f"\nScreen Context: {vision_ctx}"

        ctx_hash = hashlib.sha256(context.encode('utf-8')).hexdigest()
        if self._last_context_hash == ctx_hash:
            return
            
        self._last_context_hash = ctx_hash

        prompt = f"""
        You are Jarvis's proactive subsystem. Analyze the following user context:
        {context}
        
        Is there anything critical the user needs to be warned about (like VERY high CPU >90%), 
        or anything extremely obvious you can offer help with based on the screen?
        
        If NO, output strictly "NONE".
        If YES, output in this exact format:
        AUTONOMOUS_ACTION: <a concise command as if spoken by the user to address the issue>
        Example: "AUTONOMOUS_ACTION: close heavy background apps"
        Do not output JSON, purely the action string or NONE.
        """
        
        # We use a fast, low-temp query
        response = query_ai(prompt, system_msg="You determine if proactive help is needed.").strip()
        
        if response and response.upper() != "NONE" and "NONE" not in response.upper():
            if "AUTONOMOUS_ACTION:" in response.upper():
                try:
                    action_text = response[response.upper().index("AUTONOMOUS_ACTION:") + len("AUTONOMOUS_ACTION:"):].strip()
                    if action_text:
                        logger.info(f"[PROACTIVE] Autonomous action triggered: {action_text}")
                        # We emit an announcement notification and then emit the command
                        self._bus.emit("proactive_notification", {"message": f"Sir, I am automatically running: {action_text}"})
                        self._bus.emit("command_received", {"text": action_text, "source": "autonomous"})
                except Exception as e:
                    logger.error(f"[PROACTIVE] Failed to parse action from: {response} - {e}")
            else:
                logger.info(f"[PROACTIVE] Emitting notification: {response}")
                self._bus.emit("proactive_notification", {"message": response})

_engine: Optional[ProactiveEngine] = None

def get_proactive_engine(event_bus=None) -> ProactiveEngine:
    global _engine
    if _engine is None:
        if event_bus is None:
            raise ValueError("event_bus must be provided for initial setup of ProactiveEngine")
        _engine = ProactiveEngine(event_bus)
    return _engine
