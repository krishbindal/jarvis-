import sys
import os

# Add parent path to import correctly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.event_bus import EventBus
from brain.proactive_engine import get_proactive_engine
import time

def main():
    bus = EventBus()
    
    def on_command(payload):
        print(f"\n[MOCK] Task Planner received autonomous command: {payload['text']} (Source: {payload.get('source')})")
        
    def on_notification(payload):
        print(f"\n[MOCK] TTS Engine speaking: {payload['message']}")

    bus.subscribe("command_received", on_command)
    bus.subscribe("proactive_notification", on_notification)

    print("Starting Proactive Engine with a 10 second interval...")
    engine = get_proactive_engine(bus)
    engine._interval = 10 
    engine.start()

    print("Simulating High CPU environment implicitly via main processes... (It uses actual system stats)")
    print("Wait for about ~15 seconds for the engine to boot and poll.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping engine...")
        engine.stop()

if __name__ == "__main__":
    main()
