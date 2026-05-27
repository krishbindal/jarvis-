import os
import sys
import time
import threading

# Standardize path
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root not in sys.path: sys.path.append(root)

from triggers.clap_detector import ClapDetector
from voice.voice_input import VoiceListener
from utils import EventBus
from utils.logger import get_logger

logger = get_logger("TRIGGER-VERIFY")

def verify_triggers():
    event_bus = EventBus()
    
    print("\n" + "="*60)
    print(" JARVIS-X: SENSOR VERIFICATION SUITE")
    print("="*60)
    print("This script will check if your hardware detects Claps and the Wake Word.")
    
    # Track states
    status = {"claps": 0, "wake": False}
    
    def on_wake(payload=None):
        print("\n[DETECTED] >> WAKE WORD 'JARVIS' <<")
        status["wake"] = True

    def on_clap():
        status["claps"] += 1
        print(f"\n[DETECTED] >> CLAP EVENT #{status['claps']} <<")

    event_bus.subscribe("jarvis_wake", on_wake)
    
    # 1. Initialize Sensors
    print("\n[1/2] Initializing Clap Detector...")
    clap = ClapDetector(on_double_clap=on_clap, event_bus=event_bus)
    clap.start()
    
    print("\n[2/2] Initializing Voice Listener (Wake Word)...")
    voice = VoiceListener(event_bus=event_bus)
    voice.start()
    
    print("\n" + "-"*60)
    print(" SENSORS ACTIVE: Listening now...")
    print(" ACTION REQUIRED:")
    print(" 1. Clap twice quickly (Double-Clap).")
    print(" 2. Say 'Jarvis' clearly.")
    print(" (Press Ctrl+C to finish)")
    print("-"*60 + "\n")

    try:
        start_time = time.time()
        while time.time() - start_time < 30: # 30 second test window
            time.sleep(0.5)
            if status["claps"] > 0 and status["wake"]:
                print("\n[SUCCESS] Both triggers verified successfully!")
                break
    except KeyboardInterrupt:
        pass
    finally:
        print("\nShutting down sensors...")
        clap.stop()
        voice.stop()
        
    print("\n" + "="*60)
    print(" TEST RESULTS:")
    print(f" - Double Claps Detected: {status['claps']}")
    print(f" - 'Jarvis' Wake Word: {'DETECTED' if status['wake'] else 'NOT DETECTED'}")
    print("="*60)

if __name__ == "__main__":
    verify_triggers()
