"""
JARVIS-X Phase 17: Proactive Engine

This engine runs in the background, consuming data from VisionProvider,
SystemMonitor, and the EventBus. It decides whether to proactively
notify the user (e.g., "High CPU usage", or "Can I help with that code?").
"""

import threading
import time
from typing import Optional

from utils.logger import get_logger
from utils.system_context import get_system_stats
from brain.vision_provider import get_visual_context
from brain.ai_engine import query_ai
from core.event_bus import get_bus

logger = get_logger("jarvis.proactive")

class ProactiveEngine:
    def __init__(self, interval_seconds: int = 60):
        self._interval = interval_seconds
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._bus = get_bus()

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

        prompt = f"""
        You are Jarvis's proactive subsystem. Analyze the following user context:
        {context}
        
        Is there anything critical the user needs to be warned about (like VERY high CPU >90%), 
        or anything extremely obvious you can offer help with based on the screen?
        
        If NO, output strictly "NONE".
        If YES, output a short 1-sentence notification to show on the screen (e.g. "Sir, CPU is high. Should I clear background apps?").
        Do not output JSON, purely the notification string or NONE.
        """
        
        # We use a fast, low-temp query
        response = query_ai(prompt, system_msg="You determine if proactive help is needed.").strip()
        
        if response and response.upper() != "NONE" and "NONE" not in response.upper():
            logger.info(f"[PROACTIVE] Emitting notification: {response}")
            self._bus.emit("proactive_notification", {"message": response})

_engine: Optional[ProactiveEngine] = None

def get_proactive_engine() -> ProactiveEngine:
    global _engine
    if _engine is None:
        _engine = ProactiveEngine()
    return _engine
