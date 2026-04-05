import psutil
from typing import Dict, Any, Optional

try:
    import win32gui
    import win32process
    _WIN32_AVAILABLE = True
except Exception:  # noqa: BLE001
    win32gui = None
    win32process = None
    _WIN32_AVAILABLE = False

def get_active_window_title() -> str:
    """Return the title of the current foreground window."""
    try:
        if not _WIN32_AVAILABLE:
            return "Unknown"
        hwnd = win32gui.GetForegroundWindow()
        return win32gui.GetWindowText(hwnd) or "System"
    except Exception:
        return "Unknown"

def get_system_stats() -> Dict[str, Any]:
    """Return lightweight system resource metrics."""
    try:
        return {
            "cpu_percent": psutil.cpu_percent(interval=None),
            "memory_percent": psutil.virtual_memory().percent,
            "battery_percent": psutil.sensors_battery().percent if psutil.sensors_battery() else None,
            "active_window": get_active_window_title()
        }
    except Exception:
        return {
            "cpu_percent": 0,
            "memory_percent": 0,
            "battery_percent": None,
            "active_window": "System"
        }

def get_active_process_name() -> str:
    """Return the name of the active process (e.g., 'chrome.exe')."""
    try:
        if not _WIN32_AVAILABLE:
            return "Unknown"
        hwnd = win32gui.GetForegroundWindow()
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        process = psutil.Process(pid)
        return process.name()
    except Exception:
        return "Unknown"
