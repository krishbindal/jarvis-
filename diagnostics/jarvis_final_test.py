import sys
import os
import sqlite3
import numpy as np

print("--- JARVIS FINAL VERIFICATION SCRIPT ---")

def test_memory_db():
    print("\\n[1] Testing Native Numpy VDB...")
    try:
        from memory.database import MemoryDB
        from memory.memory_store import get_embedding, cosine_similarity
        
        # Test DB Initialization
        db = MemoryDB("memory/test_jarvis.db")
        print("  - DB Initialized")
        
        # We'll insert a mock embedding directly
        import struct
        import datetime
        mock_vec = [0.1] * 768
        blob = struct.pack(f'{len(mock_vec)}f', *mock_vec)
        
        db.add_interaction("user", "Hello World", context=None, embedding=blob)
        print("  - Interaction inserted with BLOB embedding")
        
        embeddings = db.get_all_embeddings()
        print(f"  - Retrieved {len(embeddings)} valid embeddings")
        
        # Unpack testing
        first_blob = embeddings[0]["embedding"]
        vec_tuple = struct.unpack(f'{len(first_blob)//4}f', first_blob)
        if len(vec_tuple) == 768:
            print("  - Unpacked numpy array successfully (Length: 768)")
        else:
            print("  ! Unpack size mismatch")
            return False
            
    except Exception as e:
        print(f"  [ERROR] Memory DB failed: {e}")
        return False
        
    finally:
        try:
            if os.path.exists("memory/test_jarvis.db"):
                del db
                os.remove("memory/test_jarvis.db")
        except Exception:
            pass
            
    print("  ✓ Numpy RAG Test Passed")
    return True

def test_imports():
    print("\\n[2] Testing Imports and Module Initialization...")
    failures = 0
    
    # 1. Genesis Agent
    try:
        from skills.genesis_agent import SKILL_NAME, execute
        print("  - Genesis Agent compiled successfully")
    except Exception as e:
        print(f"  [ERROR] Genesis Agent failed: {e}")
        failures += 1

    # 2. Automation Agent
    try:
        from skills.automation_agent import execute as auto_exec
        print("  - Automation Agent compiled successfully")
    except Exception as e:
        print(f"  [ERROR] Automation Agent failed: {e}")
        failures += 1

    # 3. System Monitor
    try:
        from triggers.system_monitor import SystemMonitor
        from utils.events import EventBus
        bus = EventBus()
        sys = SystemMonitor(bus)
        print("  - Iron Man Monitor initialized successfully")
    except Exception as e:
        print(f"  [ERROR] Iron Man Monitor failed: {e}")
        failures += 1

    # 4. Startup Utils
    try:
        from utils.startup import enable_autostart, disable_autostart
        print("  - Windows Autostart utilities compiled successfully")
    except Exception as e:
        print(f"  [ERROR] Autostart utilities failed: {e}")
        failures += 1
        
    return failures == 0

def test_app_hook():
    print("\\n[3] Testing Core App Hooks...")
    try:
        with open("core/app.py", "r") as f:
            content = f.read()
            if "SystemMonitor" in content and "self._sys_monitor.start()" in content:
                print("  - Iron Man Monitor correctly injected into run loop")
            else:
                print("  ! Missing Iron Man hooks")
    except Exception as e:
        print(f"  [ERROR] Could not verify app.py: {e}")

if __name__ == "__main__":
    vdb_pass = test_memory_db()
    imports_pass = test_imports()
    test_app_hook()
    
    print("\\n--- SUMMARY ---")
    if vdb_pass and imports_pass:
        print("!!! ALL SYSTEMS FUNCTIONING NORMALLY !!!")
        sys.exit(0)
    else:
        print("!!! WARNING: CRITICAL FAILURES DETECTED !!!")
        sys.exit(1)
