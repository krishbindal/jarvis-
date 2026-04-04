import time
from core.app import JarvisApp
from utils.logger import get_logger

logger = get_logger("integration_test")

def main():
    # We set auto_start=True so we don't block waiting for claps
    # We don't call app.run() because that starts infinite loops/UI
    app = JarvisApp(auto_start=True)
    
    commands = [
        "open chrome",
        "open youtube",
        "list files",
        "download video"
    ]
    
    for cmd in commands:
        logger.info(f"--- INJECTING: {cmd} ---")
        app._events.emit("command_received", {"text": cmd, "source": "voice"})
        time.sleep(2)  # Give time for async/threaded handling
        
if __name__ == "__main__":
    main()
