import os
import sys
import json
import sqlite3
import requests
import subprocess
import threading
import time
from datetime import datetime

# --- CONFIGURATION (Sync with Phase 13) ---
CONFIG = {
    "OLLAMA_URL": "http://localhost:11434",
    "MODELS_REQUIRED": ["llama3", "gemma:2b"],
    "DB_PATH": "memory/memory.db",
    "VOICE_MODEL": "voice/model",
    "SAFE_DIRS": ["Downloads", "Desktop", "Projects"],
    "N8N_URL": os.getenv("N8N_WEBHOOK_URL", "https://your-n8n-url/webhook/jarvis"),
    "TEST_COMMAND": "open chrome"
}

REPORT = {
    "PHASES": {},
    "STATUS": "INITIALIZING",
    "FIXED": [],
    "MANUAL_ACTION": []
}

def log_phase(phase_num, name, status, details="OK"):
    REPORT["PHASES"][f"PHASE_{phase_num}"] = {"name": name, "status": status, "details": details}
    print(f"[PHASE {phase_num}] {name}: {status}")

# --- PHASE 1: OLLAMA ---
def check_ollama():
    try:
        resp = requests.get(f"{CONFIG['OLLAMA_URL']}/api/tags", timeout=5)
        if resp.status_code == 200:
            models = [m['name'].split(':')[0] for m in resp.json().get('models', [])]
            missing = [m for m in CONFIG['MODELS_REQUIRED'] if m not in models]
            if missing:
                for m in missing:
                    REPORT["MANUAL_ACTION"].append(f"Run 'ollama pull {m}' to enable local fallback.")
                log_phase(1, "Ollama", "WARNING", f"Missing models: {missing}")
            else:
                log_phase(1, "Ollama", "OK")
        else:
            log_phase(1, "Ollama", "ERROR", "Service returned non-200")
    except Exception as e:
        log_phase(1, "Ollama", "ERROR", f"Connection failed: {str(e)}")

# --- PHASE 2/11: ENV & DOTENV ---
def check_env():
    from dotenv import load_dotenv
    load_dotenv()
    keys = ["GEMINI_API_KEY", "OPENROUTER_API_KEY"]
    missing = [k for k in keys if not os.getenv(k)]
    if missing:
        REPORT["MANUAL_ACTION"].append(f"Set missing keys in .env: {missing}")
        log_phase(2, "Online AI", "WARNING", f"Missing: {missing}")
    else:
        log_phase(2, "Online AI", "OK")

# --- PHASE 3: FILE SYSTEM ---
def check_filesystem():
    for d in CONFIG['SAFE_DIRS']:
        if not os.path.exists(d):
            os.makedirs(d)
            REPORT["FIXED"].append(f"Created directory: {d}")
    log_phase(3, "File System", "OK")

# --- PHASE 4: MICROPHONE ---
def check_mic():
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        input_devs = [d for d in devices if d['max_input_channels'] > 0]
        if not input_devs:
            log_phase(4, "Microphone", "ERROR", "No input devices found")
        else:
            log_phase(4, "Microphone", "OK", f"Found {len(input_devs)} inputs")
    except Exception as e:
        log_phase(4, "Microphone", "WARNING", f"Could not query devices: {str(e)}")

# --- PHASE 5: VOSK ---
def check_vosk():
    if os.path.exists(CONFIG['VOICE_MODEL']):
        subs = ["am", "conf", "graph"]
        missing = [s for s in subs if not os.path.exists(os.path.join(CONFIG['VOICE_MODEL'], s))]
        if missing:
            log_phase(5, "Vosk Model", "ERROR", f"Missing subdirs: {missing}")
        else:
            log_phase(5, "Vosk Model", "OK")
    else:
        log_phase(5, "Vosk Model", "ERROR", "Model path missing")

# --- PHASE 7: DATABASE ---
def check_db():
    try:
        os.makedirs("memory", exist_ok=True)
        conn = sqlite3.connect(CONFIG['DB_PATH'])
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS interactions (id INTEGER PRIMARY KEY, text TEXT, response TEXT, timestamp DATETIME)")
        cursor.execute("CREATE TABLE IF NOT EXISTS memory (key TEXT PRIMARY KEY, value TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS preferences (key TEXT PRIMARY KEY, value TEXT)")
        conn.commit()
        conn.close()
        log_phase(7, "Database", "OK")
    except Exception as e:
        log_phase(7, "Database", "ERROR", str(e))

# --- PHASE 8: RAG & EMBEDDINGS ---
def check_rag():
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer('all-MiniLM-L6-v2')
        test_emb = model.encode(["Hello Jarvis"])
        if test_emb.any():
            log_phase(8, "RAG/Embeddings", "OK")
    except Exception as e:
        log_phase(8, "RAG/Embeddings", "ERROR", str(e))

# --- PHASE 9/13/14: INTEGRATION TEST ---
def run_full_test():
    # Detect Chrome on Windows
    paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    ]
    found = False
    for p in paths:
        if os.path.exists(p):
            found = True
            break
    
    if found:
        log_phase(9, "Execution (Chrome)", "OK")
    else:
        REPORT["MANUAL_ACTION"].append("Chrome installation path not detected. Update system_executor.py")
        log_phase(9, "Execution (Chrome)", "WARNING", "Executable not found at default paths")

def main():
    print("🚀 JARVIS-X DEXTER COPILOT: PRE-FLIGHT CHECK")
    print("-" * 40)
    
    check_ollama()
    check_env()
    check_filesystem()
    check_mic()
    check_vosk()
    check_db()
    check_rag()
    run_full_test()
    
    print("-" * 40)
    status = "READY" if not any(p['status'] == "ERROR" for p in REPORT["PHASES"].values()) else "NOT READY"
    REPORT["STATUS"] = status
    
    print(f"🏁 FINAL STATUS: {status}")
    
    # Save Report
    with open("setup_report.json", "w") as f:
        json.dump(REPORT, f, indent=4)
    print(f"\nReport saved to setup_report.json")

if __name__ == "__main__":
    main()
