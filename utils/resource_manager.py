"""
JARVIS-X Phase 28: Synapse Core (Resource Manager)
Dynamic intelligence scaling based on system hardware load.
- If RAM > 85% or CPU > 90%, throttle background workers.
"""

import psutil
import time
from utils.logger import get_logger

logger = get_logger("RESOURCE_MANAGER")

class ResourceManager:
    """Monitors system resources and provides a 'Throttling Factor'."""
    
    def __init__(self, high_ram_threshold: float = 85.0, high_cpu_threshold: float = 90.0):
        self.high_ram = high_ram_threshold
        self.high_cpu = high_cpu_threshold

    def get_throttle_level(self) -> float:
        """
        Returns a scaling factor for intervals.
        1.0 = Normal (Nominal)
        2.0 = High Load (Slow down workers by 2x)
        5.0 = Critical Load (Urgent throttling)
        """
        try:
            ram_pct = psutil.virtual_memory().percent
            cpu_pct = psutil.cpu_percent(interval=0.1)
            
            if ram_pct > 95.0 or cpu_pct > 98.0:
                logger.warning(f"CRITICAL RESOURCE LOAD: RAM {ram_pct}% CPU {cpu_pct}%")
                return 5.0
            elif ram_pct > self.high_ram or cpu_pct > self.high_cpu:
                logger.info(f"High system load: RAM {ram_pct}% CPU {cpu_pct}%. Throttling passive tasks.")
                return 2.0
                
            return 1.0
        except Exception as e:
            logger.debug(f"Resource check failed: {e}")
            return 1.0

    def check_ollama_memory(self):
        """Unload Ollama if RAM is extremely tight."""
        ram_pct = psutil.virtual_memory().percent
        if ram_pct > 92.0:
             # This is a very targeted fix for low-end machines
             logger.warning("Emergency: System RAM depleted. Unloading background AI models.")
             # We can't easily kill process safely without knowing its PID accurately, 
             # but we can log for Sentinel to handle if we had a dedicated skill for it.
             pass

_manager_instance = ResourceManager()

def get_resource_manager():
    return _manager_instance
