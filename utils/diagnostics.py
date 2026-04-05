import os
import requests
from config import GEMINI_API_KEY, GROQ_API_KEY, MODEL_NAME
from utils.logger import get_logger

logger = get_logger(__name__)

def run_diagnostics():
    """Run a system health check (Sentinel Doctor)."""
    print("\n--- [SENTINEL DOCTOR] ---")
    print("Initiating System Diagnostics...\n")
    
    issues_found = 0
    
    # 1. API Keys
    print("1. Checking External Credentials...")
    if GROQ_API_KEY:
        print("   [OK] Groq API Key found.")
    else:
        print("   [WARN] Groq API Key missing. Fast cloud responses disabled.")
        issues_found += 1
        
    if GEMINI_API_KEY:
        print("   [OK] Gemini API Key found.")
    else:
        print("   [WARN] Gemini API Key missing. Cloud fallback & Vision disabled.")
        issues_found += 1

    # 2. Local Ollama Health
    print("\n2. Checking Local Inference Engine (Ollama)...")
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=3)
        if resp.status_code == 200:
            models = [m['name'] for m in resp.json().get('models', [])]
            if any(MODEL_NAME in m for m in models):
                print(f"   [OK] Ollama is running and '{MODEL_NAME}' is available.")
            else:
                print(f"   [WARN] Ollama is running but '{MODEL_NAME}' is missing.")
                print(f"          Run: `ollama run {MODEL_NAME}` to pull it.")
                issues_found += 1
        else:
            print("   [WARN] Ollama returned an unexpected status code.")
            issues_found += 1
    except Exception:
        print("   [WARN] Ollama is not reachable on localhost:11434.")
        print("          If you don't use local models, you can ignore this.")
        issues_found += 1
        
    # 3. Audio & UI Basics
    print("\n3. Verifying required dependencies...")
    try:
        import pygame
        import mss
        import cv2
        print("   [OK] Critical UI and Media libraries present.")
    except ImportError as e:
        print(f"   [ERROR] Missing critical dependency: {e}")
        issues_found += 1
        
    print("\n--- DIAGNOSTICS COMPLETE ---")
    if issues_found == 0:
        print("SYSTEM: ALL SYSTEMS NOMINAL. You are cleared for launch.")
    else:
        print(f"SYSTEM: {issues_found} potential issues detected.")
        print("You may proceed, but some subsystem features may be disabled.")
