"""
JARVIS-X Phase 26: Windows Autostart Configuration
Creates a safe `.bat` file in the user's startup folder.
"""

import os
import sys
from utils.logger import get_logger

logger = get_logger(__name__)

def enable_autostart():
    """Drops a `.bat` file into `shell:startup` to auto-run Jarvis on boot."""
    try:
        appdata = os.environ.get("APPDATA")
        if not appdata:
            logger.error("[STARTUP] APPDATA environment variable not found. Cannot configure autostart.")
            return False

        startup_dir = os.path.join(appdata, r"Microsoft\Windows\Start Menu\Programs\Startup")
        if not os.path.exists(startup_dir):
            os.makedirs(startup_dir, exist_ok=True)
            
        bat_path = os.path.join(startup_dir, "JarvisCopilot.bat")
        
        # Determine paths
        working_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        main_py = os.path.join(working_dir, "main.py")
        
        # Use pythonw to avoid leaving an empty console window hanging open
        python_exe = sys.executable
        if python_exe.endswith("python.exe"):
            python_exe = python_exe.replace("python.exe", "pythonw.exe")
            
        with open(bat_path, "w") as f:
            f.write("@echo off\n")
            f.write(f"cd /d \"{working_dir}\"\n")
            f.write(f"start \"\" \"{python_exe}\" \"{main_py}\"\n")
            
        logger.info(f"[STARTUP] Successfully configured Windows Autostart at {bat_path}")
        return True
    except Exception as e:
        logger.error(f"[STARTUP] Failed to configure autostart: {e}")
        return False

def disable_autostart():
    """Removes the `.bat` file."""
    try:
        appdata = os.environ.get("APPDATA")
        bat_path = os.path.join(appdata, r"Microsoft\Windows\Start Menu\Programs\Startup", "JarvisCopilot.bat")
        if os.path.exists(bat_path):
            os.remove(bat_path)
            logger.info("[STARTUP] Autostart disabled.")
        return True
    except Exception as e:
        logger.error(f"[STARTUP] Failed to disable autostart: {e}")
        return False
