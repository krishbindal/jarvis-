import sys
import json
from brain.ai_engine import interpret_command

questions = [
    "Hello Jarvis, are you online?",
    "What is your primary directive?",
    "Do you remember my name? I am Krish."
]

print("Initializing JARVIS-X Brain Test Protocol...\n")

history = []

for idx, q in enumerate(questions):
    print(f"User: {q}")
    response = interpret_command(q, history=history)
    
    # Simulate adding to history
    history.append({
        "user_input": q,
        "steps": response.get("steps", []),
        "result": {"status": "success", "message": response.get("message", "")}
    })
    
    print(f"JARVIS: {response.get('message', 'No message')}")
    if response.get("steps"):
        print(f"JARVIS [Action]: {json.dumps(response.get('steps'))}")
    print("-" * 50)
