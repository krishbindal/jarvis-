"""
JARVIS-X Phase 13: Full System Integration Simulation

This script verifies the entire pipeline:
[INPUT] -> [ROUTER] -> [ACTION] -> [EXECUTOR] -> [MEMORY]
"""

import time
import os
from core.app import JarvisApp
from utils import EventBus
from memory.memory_store import get_recent_history

def run_simulation():
    print("=== JARVIS-X INTEGRATION SIMULATION ===")
    
    # Initialize App in auto_start mode to bypass clap detection
    app = JarvisApp(auto_start=True)
    events = app._events
    
    # We won't call app.run() as it blocks. We'll manually trigger the event.
    print("[*] Simulating command: 'open google.com'")
    
    # 1. Emit command
    events.emit("command_received", {"text": "open google.com", "source": "simulation"})
    
    # Wait for processing
    time.sleep(2)
    
    # 2. Check Memory
    print("[*] Verifying memory persistence...")
    history = get_recent_history(limit=1)
    if history and "google.com" in history[0].get("user_input", ""):
        print("[SUCCESS] Command recorded in neural memory.")
    else:
        print("[FAILURE] Command not found in recent history.")

    # 3. Test Multi-step
    print("\n[*] Simulating multi-step: 'create folder test_sim and open it'")
    events.emit("command_received", {"text": "create folder test_sim and open it", "source": "simulation"})
    
    time.sleep(3)
    
    # Clean up simulation folder
    sim_folder = os.path.expanduser("~/Documents/test_sim")
    if os.path.exists(sim_folder):
        print(f"[SUCCESS] Multi-step created folder: {sim_folder}")
        try:
            os.rmdir(sim_folder)
            print("[*] Cleaned up simulation folder.")
        except:
            pass
    else:
        # Check current dir as fallback
        if os.path.exists("test_sim"):
            print("[SUCCESS] Multi-step created folder in current dir.")
            os.rmdir("test_sim")
        else:
            print("[FAILURE] Multi-step folder creation failed.")

    print("\n=== SIMULATION COMPLETED ===")

if __name__ == "__main__":
    run_simulation()
