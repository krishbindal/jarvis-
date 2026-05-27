import sys
import os
import time
import threading

# Add current directory to path
sys.path.append(os.getcwd())

import config
from core.app import JarvisApp
from utils.events import EventBus

def test_startup_logic():
    print("--- Testing Startup Logic ---")
    # Initialize app with auto_start=False (as set in main.py)
    app = JarvisApp(auto_start=False)
    
    print(f"Auto-start status: {app.auto_start}")
    if not app.auto_start:
        print("PASS: JarvisApp initialized with auto_start=False")
    else:
        print("FAIL: JarvisApp initialized with auto_start=True")

def test_config_values():
    print("\n--- Testing Config Values ---")
    print(f"Wake word: {config.WAKE_WORD}")
    if config.WAKE_WORD == "jarvis":
        print("PASS: WAKE_WORD is 'jarvis'")
    else:
        print("FAIL: WAKE_WORD is not 'jarvis'")

def test_voice_listener_config():
    print("\n--- Testing VoiceListener Config ---")
    bus = EventBus()
    from voice.voice_input import VoiceListener
    try:
        listener = VoiceListener(bus)
        print(f"Ambient mode: {listener.ambient_mode}")
        print(f"Listening for command: {listener._listening_for_command}")
        
        if listener.ambient_mode and not listener._listening_for_command:
            print("PASS: VoiceListener correctly configured for wake word detection")
        else:
            print("FAIL: VoiceListener configuration mismatch")
            
    except Exception as e:
        print(f"ERROR: Could not initialize VoiceListener: {e}")

if __name__ == "__main__":
    test_startup_logic()
    test_config_values()
    test_voice_listener_config()
