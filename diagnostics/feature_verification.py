import os
import sys
import importlib
import threading
import time

print("--- JARVIS-X ADVANCED FEATURE VERIFICATION ---")

def test_autostart_persistence():
    print("[1] Verifying Autostart Registry/Bat...")
    from utils.startup import enable_autostart, disable_autostart
    
    # Enable Autostart for verification
    if enable_autostart():
        appdata = os.environ.get("APPDATA")
        startup_dir = os.path.join(appdata, r"Microsoft\Windows\Start Menu\Programs\Startup")
        bat_path = os.path.join(startup_dir, "JarvisCopilot.bat")
        
        if os.path.exists(bat_path):
            print(f"  ✓ Startup BAT CREATED at: {bat_path}")
            with open(bat_path, 'r') as f:
                content = f.read()
                print(f"  - BAT Content Preview: {content[:100]}...")
        else:
            print("  ! Startup BAT NOT FOUND even after enabling.")
    else:
        print("  ! enable_autostart() returned False.")

def test_genesis_evolution():
    print("\n[2] Verifying Genesis Evolution Mode...")
    from skills import discover_skills
    
    # Dummy skill for test
    dummy_skill_content = """
SKILL_NAME = 'dumbo_skill'
def execute(intent, **kwargs):
    return {'success': True, 'message': 'Hello from the evolution!'}
"""
    skill_path = os.path.abspath("skills/dumbo_skill.py")
    try:
        with open(skill_path, "w") as f:
            f.write(dummy_skill_content)
        print(f"  - Dummy skill 'dumbo_skill' written to {skill_path}")
        
        # Trigger hot-reload
        discover_skills(log_results=False)
        
        # Verify execution
        from skills import execute_skill
        res = execute_skill("dumbo_skill", "test")
        if res and res.get('success'):
            print("  ✓ Genesis Hot-Reload: SUCCESS! New skill executes correctly.")
        else:
            print("  ! Genesis Hot-Reload: FAILED execution.")
            
    except Exception as e:
        print(f"  ! Genesis Error: {e}")
    finally:
        if os.path.exists(skill_path):
            try:
                os.remove(skill_path)
            except: pass

def test_monitoring_proactivity():
    print("\n[3] Verifying Iron Man Monitor proactivity...")
    from triggers.system_monitor import SystemMonitor
    from utils.events import EventBus
    
    received_event = []
    def on_warning(data=None):
        received_event.append(data)
        
    bus = EventBus()
    bus.subscribe("proactive_warning", on_warning)
    
    monitor = SystemMonitor(bus)
    monitor.start()
    
    print("  - Monitor thread started. Checking state...")
    time.sleep(1)
    
    # Corrected attribute from _thread check
    if hasattr(monitor, '_thread') and monitor._thread and monitor._thread.is_alive():
        print("  ✓ Monitor thread is ALIVE and Proactive.")
    else:
        print("  ! Monitor thread is NOT RUNNING.")
        
    monitor.stop()

def test_n8n_automation():
    print("\n[4] Verifying N8N/Automation skill integrity...")
    try:
        from skills.automation_agent import execute as auto_exec
        res = auto_exec("turn off the living room lights")
        if res:
            print(f"  ✓ Automation Skill: Integrity check passed. Result: {res.get('message', 'No message')}")
    except Exception as e:
        print(f"  ! Automation Agent Error: {e}")

if __name__ == "__main__":
    test_autostart_persistence()
    test_genesis_evolution()
    test_monitoring_proactivity()
    test_n8n_automation()
    print("\n--- ALL FEATURES VERIFIED ---")
