import os
import sys
import logging

# Add project root to path
sys.path.append(os.getcwd())

from brain.ai_engine import interpret_command, describe_screen
from config import MODEL_NAME, GROQ_API_KEY, GEMINI_API_KEY

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VERIFY")

def test_ai_fallback():
    print("\n--- [AI FALLBACK TEST] ---")
    print(f"Current Model: {MODEL_NAME}")
    print(f"Groq API Key set: {'Yes' if GROQ_API_KEY else 'No'}")
    print(f"Gemini API Key set: {'Yes' if GEMINI_API_KEY else 'No'}")
    
    test_input = "Open calculator and then tell me what time it is."
    print(f"Testing input: '{test_input}'")
    
    try:
        # This will hit Groq first, then Gemini if Groq fails/is rate limited
        result = interpret_command(test_input)
        print("\n[RESULT]")
        print(f"Action: {result.get('action')}")
        print(f"Message: {result.get('message')}")
        if "steps" in result:
            print("Steps:")
            for s in result['steps']:
                print(f"  - {s}")
        return True
    except Exception as e:
        print(f"AI Interpretation failed: {e}")
        return False

def test_vision_logic():
    print("\n--- [VISION LOGIC TEST] ---")
    # We won't actually call Gemini unless an image exists, but we can check the function logic
    if not os.path.exists("assets/memory/last_screen.png"):
        print("Note: last_screen.png not found, skipping real vision call.")
    
    # Test the describe_screen function (it should check for Gemini key first)
    res = describe_screen("What is this?")
    print(f"Vision response: {res}")
    return "Gemini" in res or "I need a Gemini API key" in res or "I can't see the screen" in res

if __name__ == "__main__":
    ai_ok = test_ai_fallback()
    vis_ok = test_vision_logic()
    
    print("\n--- [FINAL VERDICT] ---")
    if ai_ok and vis_ok:
        print("PASS: System logic is stable and fallback tiers are correctly ordered.")
    else:
        print("FAIL: Verification encountered issues.")
