"""
JARVIS-X Phase 26: Iron Man Monitor (Armor Upgrade)
A proactive background daemon that watches system health, including RAM, Disk, and App Responsiveness.
"""

import threading
import time
import os
import psutil
import win32gui
import win32process
import ctypes
from typing import Optional, List
from utils.logger import get_logger
from utils.events import EventBus

logger = get_logger(__name__)

class SystemMonitor:
    """Monitors system memory, CPU, disk, and window health in the background."""

    def __init__(self, event_bus: EventBus, interval_sec: int = 15):
        self._events = event_bus
        self._interval = interval_sec
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_warn_time = 0
        self._last_disk_check = 0
        self._unresponding_pids = set()

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True, name="SystemMonitor")
        self._thread.start()
        logger.info("[ARMOR] Iron Man System Monitor & Mechanic activated.")

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
            
    def _is_window_responding(self, hwnd) -> bool:
        """Check if a window is responding using Win32 API."""
        try:
            user32 = ctypes.windll.user32
            # IsHungAppWindow returns true if the app is NOT responding
            return not user32.IsHungAppWindow(hwnd)
        except Exception:
            return True

    def _check_disk_health(self) -> None:
        """Monitor primary drive space."""
        now = time.time()
        if now - self._last_disk_check < 3600: # Check disk once per hour
            return
            
        try:
            # Check C:\ on Windows
            usage = psutil.disk_usage('C:\\')
            if usage.percent > 90.0:
                free_gb = usage.free / (1024**3)
                msg = f"Sir, drive C is nearly full ({free_gb:.1f} GB remaining). Shall I perform a system cleanup to free up space?"
                self._events.emit("proactive_suggestion", msg)
                logger.warning(f"[ARMOR] Low disk space: {usage.percent}%")
            self._last_disk_check = now
        except Exception as e:
            logger.error(f"[MONITOR] Disk check error: {e}")

    def _check_app_health(self) -> None:
        """Detect unresponsive application windows."""
        hwnds: List[int] = []
        def callback(hwnd, extra):
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                extra.append(hwnd)
        
        try:
            win32gui.EnumWindows(callback, hwnds)
            for hwnd in hwnds:
                if not self._is_window_responding(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if not title: continue
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    if pid not in self._unresponding_pids:
                        msg = f"Sir, it appears that {title} is not responding. Would you like me to attempt a restart of the application?"
                        self._events.emit("proactive_warning", msg)
                        self._unresponding_pids.add(pid)
                        logger.warning(f"[ARMOR] Unresponsive window found: {title} (PID {pid})")
                else:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    self._unresponding_pids.discard(pid)
        except Exception as e:
            logger.debug(f"[MONITOR] App health check trace: {e}")

    def _monitor_loop(self) -> None:
        while self._running:
            try:
                # 1. RAM Check
                mem = psutil.virtual_memory()
                if mem.percent > 90.0:
                    now = time.time()
                    if now - self._last_warn_time > 300:
                        self._check_ram_offender()
                        self._last_warn_time = now

                # 2. Disk Check
                self._check_disk_health()

                # 3. Responsive App Check
                self._check_app_health()
                
            except Exception as e:
                logger.error(f"[MONITOR] Loop error: {e}")

            time.sleep(self._interval)

    def _check_ram_offender(self) -> None:
        biggest_proc = None
        max_mem = 0
        for p in psutil.process_iter(['name', 'memory_percent']):
            try:
                if p.info['memory_percent'] and p.info['memory_percent'] > max_mem:
                    max_mem = p.info['memory_percent']
                    biggest_proc = p.info['name']
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        if biggest_proc:
            msg = f"Sir, system memory is at capacity. {biggest_proc} is consuming high resources. Shall I investigate?"
        else:
            msg = "Sir, system memory has exceeded 90 percent."

        self._events.emit("proactive_warning", msg)
