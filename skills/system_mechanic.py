"""
JARVIS-X Phase 26: System Mechanic
Skills for self-healing, process recovery, and system maintenance.
"""

import os
import shutil
import psutil
from typing import Dict, List, Any
from utils.logger import get_logger

logger = get_logger(__name__)

SKILL_NAME = "system_mechanic"
SKILL_DESCRIPTION = "Provides system cleanup and process recovery for the Armor update."
SKILL_PATTERNS = [
    r"(?:perform|run|do) (?:system )?cleanup",
    r"clear (?:temp|temporary) files",
    r"fix (?:unresponsive|hanging) (?:apps|app|windows|window)",
    r"system health summary"
]

class SystemMechanic:
    """Skill to repair/maintain system health."""

    def __init__(self):
        self._temp_paths = [
            os.environ.get("TEMP"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Temp"),
        ]

    def perform_cleanup(self) -> Dict[str, Any]:
        """Clear temporary files to free up disk space."""
        freed_bytes = 0
        deleted_count = 0
        errors = 0

        for path in self._temp_paths:
            if not path or not os.path.exists(path):
                continue
            
            logger.info(f"[MECHANIC] Cleaning temp path: {path}")
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                try:
                    if os.path.isfile(item_path) or os.path.islink(item_path):
                        size = os.path.getsize(item_path)
                        os.unlink(item_path)
                        freed_bytes += size
                        deleted_count += 1
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path, ignore_errors=True)
                        deleted_count += 1
                except Exception:
                    errors += 1

        freed_mb = freed_bytes / (1024 * 1024)
        return {
            "freed_mb": round(freed_mb, 2),
            "files_cleared": deleted_count,
            "errors": errors
        }

    def handle_unresponsive_app(self, pid: int) -> bool:
        """Attempt to gracefully close or force-kill an unresponsive app."""
        try:
            p = psutil.Process(pid)
            p.terminate()
            return True
        except Exception:
            return False

    def check_health_summary(self) -> str:
        """Get a textual summary of system health."""
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory().percent
        disk = psutil.disk_usage('C:\\').percent
        return f"System CPU is at {cpu} percent, memory at {mem} percent, and primary drive usage is {disk} percent."

def execute(target: str, extra: Dict[str, Any]) -> Dict[str, Any]:
    """Execute mechanic actions."""
    mechanic = SystemMechanic()
    
    if "cleanup" in target.lower() or "cleanup" in extra.get("action", ""):
        res = mechanic.perform_cleanup()
        return {
            "success": True,
            "status": "success",
            "message": f"Sir, I have successfully cleared {res['files_cleared']} temporary files, freeing up {res['freed_mb']} MB of space.",
            "output": res
        }
    
    if "fix" in target.lower() or "pid" in extra:
        pid = extra.get("pid")
        if pid:
            success = mechanic.handle_unresponsive_app(int(pid))
            msg = f"Sir, I have attempted to reclaim PID {pid}. System stability should improve." if success else "Sir, I was unable to close the process."
            return {"success": success, "status": "success" if success else "error", "message": msg}

    # Default: summary
    summary = mechanic.check_health_summary()
    return {"success": True, "status": "success", "message": f"Sir, {summary}", "output": summary}
