import sys
import os
import json

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.command_router import route_command
from skills import match_skill

def test_command(text):
    print(f"\n[TESTING] Command: '{text}'")
    
    # 1. Check Skill System (n8n, music, etc)
    skill = match_skill(text)
    if skill:
        print(f"  -> Routed to Skill: {skill['skill_name']}")
        print(f"  -> Description: {skill['description']}")
        return
        
    # 2. Check Core Router
    result = route_command(text)
    if isinstance(result, list):
        print(f"  -> Multi-step detected ({len(result)} steps)")
        for i, r in enumerate(result):
            print(f"    Step {i+1}: Action={r['action']}, Target='{r['target']}'")
    else:
        print(f"  -> Routed to: Action={result['action']}, Target='{result['target']}', Message='{result['message']}'")

if __name__ == "__main__":
    commands = [
        "open whatsapp and text krish hii",
        "open chrome, then youtube on a tab and play any song",
        "convert a word file to pdf",
        "download any song for me",
        "surf web and search for free ringtone and download one ringtone",
        "open spotify and then close it"
    ]
    
    print("=== JARVIS-X UNIVERSAL WORKFLOW TEST ===")
    for cmd in commands:
        test_command(cmd)
