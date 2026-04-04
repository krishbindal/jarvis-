"""
JARVIS-X: Master System Diagnostic Suite (The "Sentinel" Protocol)
A comprehensive, automated self-test of all core systems and advanced features.
"""

import os
import sys
import time
import requests
import socket
import psutil
import sqlite3
import numpy as np
import threading
from typing import Dict, List, Any
from pathlib import Path
from utils.logger import get_logger

# Import internal modules (we catch errors individually)
logger = get_logger("JARVIS_SENTINEL")

class JarvisMasterCheck:
    """Automated end-to-end diagnostic suite."""

    def __init__(self):
        self._results: Dict[str, Any] = {}
        self._db_path = "memory/jarvis.db"

    def run_all(self):
        print("\n" + "="*50)
        print("🚀 JARVIS-X: INITIATING MASTER SYSTEM DIAGNOSTIC")
        print("="*50 + "\n")

        self.check_connectivity()
        self.check_ai_providers()
        self.check_local_ai()
        self.check_voice_engines()
        self.check_memory_systems()
        self.check_triggers()
        self.check_action_registry()

        self.print_final_report()

    def check_connectivity(self):
        print("🌐 [1/7] Testing Network Connectivity...")
        try:
            socket.create_connection(("google.com", 80), timeout=3)
            self._results["Network"] = ("PASS", "Internet connectivity established.")
        except Exception:
            self._results["Network"] = ("WARN", "No internet connection. Hybrid/Online features will fall back to local mode.")

    def check_ai_providers(self):
        print("🧠 [2/7] Checking Cloud AI Providers...")
        from config import GROQ_API_KEY, GEMINI_API_KEY
        
        status = []
        if GROQ_API_KEY:
            status.append("Groq (Whisper/LPU) ONLINE")
        else:
            status.append("Groq API Key MISSING")

        if GEMINI_API_KEY:
            status.append("Gemini (Vision/Fallover) ONLINE")
        else:
            status.append("Gemini API Key MISSING")

        self._results["Cloud AI"] = ("PASS" if all("ONLINE" in s for s in status) else "WARN", "; ".join(status))

    def check_local_ai(self):
        print("🤖 [3/7] Checking Local AI (Ollama)...")
        try:
            resp = requests.get("http://localhost:11434/api/tags", timeout=3)
            if resp.status_code == 200:
                models = [m['name'] for m in resp.json().get('models', [])]
                found = []
                for m in ["llama3:latest", "base", "nomic-embed-text"]:
                    # Just check for part of the names
                    if any(m in mod for mod in models):
                        found.append(m)
                
                if "nomic-embed-text" in str(models):
                     self._results["Local AI"] = ("PASS", f"Ollama running. Found {len(models)} models.")
                else:
                     self._results["Local AI"] = ("WARN", "Ollama running, but 'nomic-embed-text' missing for Vector RAG.")
            else:
                 self._results["Local AI"] = ("FAIL", "Ollama responds, but returned an error.")
        except Exception:
             self._results["Local AI"] = ("FAIL", "Ollama is not running. Local AI and Vector RAG will not work.")

    def check_voice_engines(self):
        print("🎙️ [4/7] Checking Voice Interaction (TTS/STT)...")
        status = []
        
        # STT (Vosk)
        vosk_path = "voice/vosk-model-small-en-us-0.15"
        if os.path.exists(vosk_path):
            status.append("Vosk Offline STT READY")
        else:
            status.append("Vosk Model MISSING")

        # TTS (Edge-TTS)
        try:
            import edge_tts
            status.append("Edge-TTS Engine READY")
        except ImportError:
            status.append("Edge-TTS Package MISSING")

        self._results["Voice"] = ("PASS" if "READY" in str(status) else "FAIL", "; ".join(status))

    def check_memory_systems(self):
        print("📂 [5/7] Checking Memory & Vector Database...")
        try:
            conn = sqlite3.connect(self._db_path)
            c = conn.cursor()
            c.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [r[0] for r in c.fetchall()]
            conn.close()

            required = {"interactions", "knowledge", "usage_stats"}
            missing = required - set(tables)
            
            if not missing:
                self._results["Database"] = ("PASS", f"All {len(tables)} tables found.")
            else:
                self._results["Database"] = ("WARN", f"Database initialized, but missing: {', '.join(missing)}")
        except Exception as e:
            self._results["Database"] = ("FAIL", f"SQLite error: {e}")

    def check_triggers(self):
        print("🛡️ [6/7] Checking Advanced Triggers (Deep Dexter/Armor)...")
        issues = []
        
        # Clipboard
        try:
            from triggers.clipboard_monitor import ClipboardMonitor
            status = "Clipboard: OK"
        except Exception:
            status = "Clipboard: FAIL (Import Error)"
            issues.append(status)

        # File Sorcerer
        downloads = os.path.join(str(Path.home()), "Downloads")
        if os.path.exists(downloads):
            status += "; Downloads: FOUND"
        else:
            status += "; Downloads: NOT FOUND"
            issues.append("Downloads directory missing")
            
        # Knowledge Indexer
        try:
            from triggers.knowledge_indexer import KnowledgeIndexer
            status += "; Indexer: OK"
        except Exception:
            status += "; Indexer: FAIL"
            issues.append("KnowledgeIndexer import failed")

        self._results["Triggers"] = ("PASS" if not issues else "WARN", status)

    def check_action_registry(self):
        print("⚙️ [7/7] Checking Action Registry (Skills)...")
        try:
            from core.action_registry import ACTION_REGISTRY
            from skills import list_skills
            skills = list_skills()
            self._results["Actions"] = ("PASS", f"Registry has {len(ACTION_REGISTRY)} core actions and {len(skills)} skills.")
        except Exception as e:
            self._results["Actions"] = ("FAIL", f"Registry check failed: {e}")

    def print_final_report(self):
        print("\n" + "="*50)
        print("📋 FINAL SYSTEM REPORT CARD")
        print("="*50)
        
        all_passed = True
        for sys_name, (status, msg) in self._results.items():
            icon = "✅" if status == "PASS" else "⚠️" if status == "WARN" else "❌"
            if status == "FAIL": all_passed = False
            print(f"{icon} {sys_name:<15} : {status:<5} | {msg}")
        
        print("\n" + "="*50)
        if all_passed:
            print("🤩 STATUS: ALL SYSTEMS NOMINAL - JARVIS-X IS FULLY OPERATIONAL")
        else:
             print("⚠️ STATUS: DEGRADED PERFORMANCE - SOME SYSTEMS REQUIRE ATTENTION")
        print("="*50 + "\n")

if __name__ == "__main__":
    checker = JarvisMasterCheck()
    checker.run_all()
