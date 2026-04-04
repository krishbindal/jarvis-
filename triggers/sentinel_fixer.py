"""
JARVIS-X Phase 26: Sentinel Fixer (Self-Healing Daemon)
Tails the jarvis.log for ERROR events and performs AI-assisted root cause analysis.
"""

import os
import time
import threading
from typing import Optional
from utils.logger import get_logger
from brain.ai_engine import query_ai

logger = get_logger("SENTINEL_FIXER")

class SentinelFixer(threading.Thread):
    """Wait for log error events and suggest a fix."""

    def __init__(self, log_path: str = "assets/logs/jarvis.log"):
        super().__init__(daemon=True, name="SentinelFixer")
        self.log_path = log_path
        self._stop_event = threading.Event()
        self._last_position = 0

    def stop(self):
        """Stop the sentinel."""
        self._stop_event.set()

    def run(self):
        """Monitor log for errors precisely."""
        logger.info("Sentinel Fixer online. Monitoring log: %s", self.log_path)
        
        # Fast-forward to end of file to ignore past errors
        if os.path.exists(self.log_path):
            self._last_position = os.path.getsize(self.log_path)

        while not self._stop_event.is_set():
            if not os.path.exists(self.log_path):
                time.sleep(2)
                continue
            
            with open(self.log_path, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(self._last_position)
                new_lines = f.readlines()
                self._last_position = f.tell()

                for line in new_lines:
                    if " - ERROR - " in line:
                        self._analyze_error(line)

            time.sleep(1)

    def _analyze_error(self, error_line: str):
        """Perform AI analysis of the error and broadcast a fix suggestion."""
        logger.warning("[SENTINEL] Error detected: %s", error_line.strip())
        
        # New Autonomous Fix Logic
        from utils.auto_repair import analyze_and_fix_error
        fix_result = analyze_and_fix_error(error_line)
        
        prompt = f"Jarvis internal error log: {error_line}\nAnalyze the root cause and provide a 1-sentence plain English fix recommendation to the user."
        
        try:
            ai_suggestion = query_ai(prompt, system_msg="You are the system self-healing sentinel.")
            
            # Combine result
            final_recommendation = f"{ai_suggestion} | {fix_result}" if fix_result != "No autonomous fix found for this error. AI analysis recommended." else ai_suggestion
            
            logger.info("[SENTINEL] Fix Recommendation: %s", final_recommendation)
            
            # Here we could emit an event for the HUD visualization
            from utils.events import get_event_bus
            bus = get_event_bus()
            bus.emit("sentinel_fix_ready", {
                "error": error_line.strip(),
                "recommendation": final_recommendation,
                "auto_fixed": "Auto-repaired" in fix_result
            })
            
        except Exception as e:
            logger.error("Sentinel failed to analyze error: %s", e)

if __name__ == "__main__":
    # Test stub
    sentinel = SentinelFixer()
    sentinel.start()
    time.sleep(5)
    sentinel.stop()
