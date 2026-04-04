import sys
import os
import json
import time

# Add roots to path
sys.path.append(os.getcwd())

from brain.ai_engine import interpret_command
from core.action_registry import execute_action
from memory.personality import get_all_preferences, set_preference

def test_learning_loop():
    print("--- 🧠 JARVIS-X LEARNING & PERSONALITY TEST ---")
    
    # 0. Clear existing test data
    set_preference("user_name", "Unknown")
    set_preference("fav_language", "None")
    
    # 1. Simulate Learning Turn
    user_input = "My name is Krish and I'm a professional Python developer. Remember that."
    print(f"\n[TURN 1] User: {user_input}")
    
    # Get AI response
    ai_result = interpret_command(user_input)
    print(f"[TURN 1] Jarvis Message: {ai_result.get('message')}")
    
    # Execute steps (should include set_personality)
    steps = ai_result.get("steps", [])
    for step in steps:
        print(f"[TURN 1] Executing Action: {step['action']} -> {step['target']}")
        execute_action(step['action'], step['target'], step.get("extra", {}))
    
    # 2. Verify Storage
    prefs = get_all_preferences()
    print(f"\n[VERIFY] Current Preferences: {json.dumps(prefs, indent=2)}")
    
    if prefs.get("user_name") == "Krish":
        print("✅ SUCCESS: Name learned.")
    else:
        print("❌ FAIL: Name NOT learned.")
        
    # 3. Simulate Recall Turn
    recall_input = "Who am I? And what's my main language?"
    print(f"\n[TURN 2] User: {recall_input}")
    
    ai_recall = interpret_command(recall_input)
    print(f"[TURN 2] Jarvis Message: {ai_recall.get('message')}")
    
    # 4. Success Check
    msg = ai_recall.get('message', '').lower()
    if "krish" in msg and "python" in msg:
        print("✅ SUCCESS: Jarvis recalled personal details.")
    else:
        print("❌ FAIL: Jarvis missed key personality context.")

    # 5. Phrasing Variance Check
    print("\n[VERIFY] Phrasing Variance Test...")
    res1 = interpret_command("Open chrome")["message"]
    res2 = interpret_command("Open chrome")["message"]
    print(f"Response 1: {res1}")
    print(f"Response 2: {res2}")
    
    if res1 != res2:
        print("✅ SUCCESS: Response phrasing is varied.")
    else:
        # Note: AI might randomly choose the same, so this is a soft check
        print("⚠️ NOTE: Responses were identical. Consider if prompt needs more 'variance' pressure.")

if __name__ == "__main__":
    test_learning_loop()
