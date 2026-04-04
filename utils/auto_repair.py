"""
JARVIS-X Phase 27: Aether Shield (Auto-Repair Manager)
Autonomous dependency fixer and configuration healer.
"""

import subprocess
import sys
import os
from typing import List, Dict
from utils.logger import get_logger

logger = get_logger("AUTO_REPAIR")

# Mapping of missing modules to pip packages
PACKAGE_MAP = {
    "cv2": "opencv-python",
    "PIL": "Pillow",
    "pyautogui": "pyautogui",
    "win32clipboard": "pywin32",
    "vosk": "vosk",
    "sounddevice": "sounddevice",
    "pyaudio": "PyAudio",
    "psutil": "psutil"
}

def attempt_pip_install(module_name: str) -> bool:
    """Attempts to install a missing module using pip."""
    package = PACKAGE_MAP.get(module_name, module_name)
    logger.warning(f"[AUTO-REPAIR] Attempting to install missing dependency: {package}")
    
    try:
        # Use sys.executable to ensure we use current Jarvis venv
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        logger.info(f"[AUTO-REPAIR] Successfully installed {package}.")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"[AUTO-REPAIR] Critical Failure: Could not install {package}. Error: {e}")
        return False

def analyze_and_fix_error(error_log: str) -> str:
    """Analyzes an error line and applies a fix if autonomous fix is available."""
    if "ModuleNotFoundError" in error_log or "No module named" in error_log:
        # Extract module name
        import re
        match = re.search(r"named '([^']+)'", error_log) or re.search(r"ModuleNotFoundError: ([^\s]+)", error_log)
        if match:
            module = match.group(1)
            success = attempt_pip_install(module)
            if success:
                return f"Auto-repaired: Installed missing module {module}."
            return f"Failed to auto-repair missing module {module}."
            
    if "Audio stream failed" in error_log or "PortAudio" in error_log:
        # Suggest/Apply PyAudio fix
        logger.warning("[AUTO-REPAIR] Detected possible PyAudio/PortAudio failure.")
        # We can't easily install PortAudio C-libs, but we can try pip.
        success = attempt_pip_install("pyaudio")
        if success:
            return "Attempted PyAudio repair for voice system."
        
    return "No autonomous fix found for this error. AI analysis recommended."

if __name__ == "__main__":
    # Test
    if len(sys.argv) > 1:
        print(analyze_and_fix_error(sys.argv[1]))
