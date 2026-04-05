"""Entry point for JARVIS-X."""
import sys
import socket
import signal
import time
from core.app import JarvisApp
from utils.startup import enable_autostart
from utils.logger import get_logger
from utils.events import EventBus

logger = get_logger(__name__)

def signal_handler(sig, frame):
    """Graceful shutdown protocol (Phase 30)."""
    print("\n[SYSTEM] Shutdown initiated (Sentinel Protocol)...")
    if "_bus" in globals() and _bus:
        _bus.emit("system_shutdown")
    
    # Give threads a tiny window to cleanup
    time.sleep(0.5)
    
    if "_lock_socket" in globals() and _lock_socket:
        try:
            _lock_socket.close()
        except:
            pass
            
    print("[SYSTEM] All systems offline. Goodbye, sir.")
    sys.exit(0)

# Register shutdown handler
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

_bus = EventBus()
_lock_socket = None

def main() -> None:
    if "--doctor" in sys.argv:
        from utils.diagnostics import run_diagnostics
        run_diagnostics()
        sys.exit(0)

    global _lock_socket
    
    # Phase 26: Singleton Enforcement (prevent double instances)
    try:
        _lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _lock_socket.bind(("localhost", 9999))
    except socket.error:
        print("\n[CRITICAL] JARVIS-X is already running!")
        print("Please check your Task Manager for any 'python.exe' or 'Jarvis' processes.")
        sys.exit(1)

    # Ensure background start on future boots
    enable_autostart()
    
    app = JarvisApp(auto_start=True)
    app.run()


if __name__ == "__main__":
    main()
