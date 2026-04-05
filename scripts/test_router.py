import sys
import os

# Add project root to sys.path
sys.path.append(os.getcwd())

from core.command_router import route_command

test_cmds = [
    "play mockingbird",
    "play music on youtube",
    "open chrome",
    "what is the weather"
]

print("--- ROUTING TEST ---")
for cmd in test_cmds:
    result = route_command(cmd)
    
    # Handle list of results
    if isinstance(result, list):
        print(f"CMD: '{cmd}' -> (Multi-step)")
        for i, step in enumerate(result):
            print(f"  Step {i+1}: {step.get('action')} - {step.get('description')}")
    else:
        # Single step
        print(f"CMD: '{cmd}' -> ACTION: {result.get('action')} (Desc: {result.get('description')})")
