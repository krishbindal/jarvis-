import time
import os
import sys
from utils.logger import get_logger

# Ensure the root directory is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.app import JarvisApp

def test_advanced_features():
    print("=== JARVIS-X ADVANCED FEATURES TEST ===")
    
    app = JarvisApp(auto_start=True)
    events = app._events
    
    # We will subscribe to 'command_result' to capture the output of Jarvis
    results = []
    def on_result(payload):
        print(f"\n[JARVIS OUTPUT] -> {payload}\n")
        results.append(payload)

    def on_progress(payload):
        print(f"[JARVIS PROGRESS] -> {payload}")

    events.subscribe("command_result", on_result)
    events.subscribe("command_progress", on_progress)
    
    commands_to_test = [
        "calculate the 15th fibonacci number using python",
        "what do you see on my screen right now?",
        "reflect on your recent performance",
    ]
    
    for cmd in commands_to_test:
        print(f"\n[*] Sending command: '{cmd}'")
        events.emit("command_received", {"text": cmd, "source": "simulation"})
        
        # Wait a bit for the background thread to finish processing
        timeout = 20
        start = time.time()
        while time.time() - start < timeout:
            if len(results) > 0:
                break
            time.sleep(0.5)
        
        if len(results) > 0:
            print(f"[SUCCESS] Got response for '{cmd}'")
            results.clear()
        else:
            print(f"[ERROR] Timeout waiting for response for '{cmd}'")

    print("\n=== TEST COMPLETED ===")

if __name__ == "__main__":
    test_advanced_features()
