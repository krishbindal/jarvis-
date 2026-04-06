"""
JARVIS-X Dexter Copilot — Full Automation Test Suite
=====================================================
Tests: Responsiveness · AI Latency · Command Routing · Execution · Memory · Behaviour
"""
from __future__ import annotations

import sys
import os
import time
import json
import sqlite3
import requests
import threading
import subprocess
from datetime import datetime
from pathlib import Path

# Bootstrap path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ──────────────────────────────────────────────────
# Colour helpers (Windows-safe)
# ──────────────────────────────────────────────────
try:
    import colorama
    colorama.init()
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    RED    = "\033[91m"
    CYAN   = "\033[96m"
    BOLD   = "\033[1m"
    RESET  = "\033[0m"
except ImportError:
    GREEN = YELLOW = RED = CYAN = BOLD = RESET = ""

# ──────────────────────────────────────────────────
# Report card
# ──────────────────────────────────────────────────
RESULTS: list[dict] = []

def record(category: str, test: str, passed: bool, detail: str = "", latency_ms: float | None = None):
    icon = f"{GREEN}✓{RESET}" if passed else f"{RED}✗{RESET}"
    lat  = f"  [{latency_ms:.0f}ms]" if latency_ms is not None else ""
    print(f"  {icon}  {test}{lat}")
    if detail:
        print(f"      {CYAN}↳ {detail}{RESET}")
    RESULTS.append({"category": category, "test": test, "passed": passed,
                    "detail": detail, "latency_ms": latency_ms})

def section(title: str):
    print(f"\n{BOLD}{CYAN}━━━ {title} ━━━{RESET}")

# ──────────────────────────────────────────────────
# TEST 1: Config & .env loading
# ──────────────────────────────────────────────────
def test_config():
    section("PHASE 1 · Config & Environment")
    try:
        import config
        record("Config", ".env loads correctly", True)
        gemini_set = bool(config.GEMINI_API_KEY)
        groq_set = bool(config.GROQ_API_KEY)
        n8n_set = (
            bool(config.N8N_WEBHOOK_URL)
            and "localhost" not in config.N8N_WEBHOOK_URL
            and "your-n8n" not in config.N8N_WEBHOOK_URL
        )

        record("Config", "GEMINI_API_KEY present", gemini_set, "set" if gemini_set else "not set")
        record("Config", "GROQ_API_KEY present", groq_set, "set" if groq_set else "not set")
        record("Config", "N8N_WEBHOOK_URL present",
               n8n_set,
               "set" if n8n_set else "not set")
        record("Config", "MODEL_NAME set",          bool(config.MODEL_NAME), config.MODEL_NAME)
    except Exception as exc:
        record("Config", "Config import", False, str(exc))

# ──────────────────────────────────────────────────
# TEST 2: Ollama service ping
# ──────────────────────────────────────────────────
def test_ollama():
    section("PHASE 2 · Ollama Local AI")
    t0 = time.monotonic()
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        latency = (time.monotonic() - t0) * 1000
        record("Ollama", "Service reachable", resp.status_code == 200, latency_ms=latency)

        models = [m["name"].split(":")[0] for m in resp.json().get("models", [])]
        for model in ["llama3", "gemma"]:
            record("Ollama", f"Model '{model}' installed", model in models,
                   "MISSING – run: ollama pull " + model if model not in models else "Ready")
    except Exception as exc:
        record("Ollama", "Service reachable", False, str(exc))

# ──────────────────────────────────────────────────
# TEST 3: AI engine latency & response quality
# ──────────────────────────────────────────────────
def test_ai_engine():
    section("PHASE 3 · AI Engine Responsiveness")
    try:
        from brain.ai_engine import interpret_command
        prompts = [
            ("what time is it",            "open_url or quick_search expected"),
            ("open chrome",                "open_app action expected"),
            ("list files on desktop",      "list_files action expected"),
            ("play music",                 "media_control action expected"),
            ("what is 2 + 2",              "quick_search or ai message"),
        ]
        for prompt, note in prompts:
            t0 = time.monotonic()
            result = interpret_command(prompt)
            latency = (time.monotonic() - t0) * 1000
            steps   = result.get("steps", [])
            msg     = result.get("message", "")
            passed  = bool(steps) or bool(msg)
            actions = [s.get("action") for s in steps] if steps else []
            record("AI", f"Prompt: '{prompt}'", passed,
                   f"Actions={actions} | Msg='{msg[:60]}'" if passed else "No response",
                   latency_ms=latency)
    except Exception as exc:
        record("AI", "AI engine import/run", False, str(exc))

# ──────────────────────────────────────────────────
# TEST 4: Command router accuracy
# ──────────────────────────────────────────────────
def test_router():
    section("PHASE 4 · Command Router Accuracy")
    try:
        from core.command_router import route_command
        cases = [
            ("open chrome",     "open_app"),
            ("open youtube",    "open_url"),
            ("pause music",     "media_control"),
            ("mute",            "media_control"),
            ("lock computer",   "power_state"),
            ("list files",      "list_files"),
            ("capture screen",  "capture_screen"),
            ("search google",   "open_url"),
        ]
        for cmd, expected_action in cases:
            t0 = time.monotonic()
            result = route_command(cmd)
            latency = (time.monotonic() - t0) * 1000
            action   = result.get("action", "")
            passed   = action == expected_action or expected_action in action
            record("Router", f"'{cmd}' → '{expected_action}'",
                   passed, f"Got: '{action}'", latency_ms=latency)
    except Exception as exc:
        record("Router", "Router import/run", False, str(exc))

# ──────────────────────────────────────────────────
# TEST 5: Executor — system commands
# ──────────────────────────────────────────────────
def test_executor():
    section("PHASE 5 · System Executor")
    try:
        from executor.system_executor import list_files, file_info, open_app

        # list_files
        t0 = time.monotonic()
        r = list_files(str(Path.home()))
        latency = (time.monotonic() - t0) * 1000
        record("Executor", "list_files(home)", r.get("success", False),
               r.get("message", "")[:80], latency_ms=latency)

        # file_info
        t0 = time.monotonic()
        r = file_info(str(Path.home()))
        latency = (time.monotonic() - t0) * 1000
        record("Executor", "file_info(home)", r.get("success", False),
               str(r.get("data", ""))[:80], latency_ms=latency)

        # open_app safety-check (just verify path detection, don't actually launch)
        from executor.system_executor import _safe_path
        chrome_paths = [
            Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
            Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
        ]
        chrome_found = any(p.exists() for p in chrome_paths)
        record("Executor", "Chrome binary detected", chrome_found,
               "Path found" if chrome_found else "Will use 'start chrome' shell fallback")

    except Exception as exc:
        record("Executor", "Executor import/run", False, str(exc))

# ──────────────────────────────────────────────────
# TEST 6: SQLite memory
# ──────────────────────────────────────────────────
def test_memory():
    section("PHASE 6 · Neural Memory (SQLite)")
    try:
        from memory.memory_store import save_interaction, get_recent_history, get_relevant_context

        # Save
        t0 = time.monotonic()
        save_interaction("test automation input", [{"action": "open_app", "target": "chrome"}],
                         {"status": "success"})
        latency = (time.monotonic() - t0) * 1000
        record("Memory", "save_interaction()", True, latency_ms=latency)

        # Retrieve recent
        t0 = time.monotonic()
        history = get_recent_history(limit=5)
        latency = (time.monotonic() - t0) * 1000
        record("Memory", "get_recent_history()", bool(history),
               f"{len(history)} entries found", latency_ms=latency)

        # Semantic search
        t0 = time.monotonic()
        relevant = get_relevant_context("open browser", limit=3)
        latency = (time.monotonic() - t0) * 1000
        record("Memory", "get_relevant_context() [semantic]",
               relevant is not None,
               f"{len(relevant)} relevant entries" if relevant else "Empty (ok on first run)",
               latency_ms=latency)

    except Exception as exc:
        record("Memory", "Memory store import/run", False, str(exc))

# ──────────────────────────────────────────────────
# TEST 7: EventBus integration
# ──────────────────────────────────────────────────
def test_eventbus():
    section("PHASE 7 · EventBus (Thread Safety)")
    try:
        from utils import EventBus
        bus = EventBus()
        received: list = []

        def handler(payload):
            received.append(payload)

        bus.subscribe("command_received", handler)

        # Emit in a thread
        t0 = time.monotonic()
        t = threading.Thread(target=bus.emit, args=("command_received", {"text": "test", "source": "test"}))
        t.start(); t.join(timeout=2)
        latency = (time.monotonic() - t0) * 1000

        record("EventBus", "Thread-safe emit & receive", len(received) == 1,
               f"Payload: {received[0] if received else 'none'}", latency_ms=latency)
    except Exception as exc:
        record("EventBus", "EventBus test", False, str(exc))

# ──────────────────────────────────────────────────
# TEST 8: Vosk model structure
# ──────────────────────────────────────────────────
def test_vosk():
    section("PHASE 8 · Vosk Voice Model")
    model_path = Path("voice/model")
    record("Voice", "voice/model directory exists", model_path.exists())
    for sub in ["am", "conf", "graph"]:
        exists = (model_path / sub).exists()
        record("Voice", f"voice/model/{sub}/ exists", exists,
               "" if exists else "Model incomplete – re-download Vosk model")

# ──────────────────────────────────────────────────
# TEST 9: Microphone presence
# ──────────────────────────────────────────────────
def test_microphone():
    section("PHASE 9 · Audio Hardware")
    try:
        import sounddevice as sd
        devs = sd.query_devices()
        input_devs = [d for d in devs if d["max_input_channels"] > 0]
        record("Audio", "Microphone devices found", bool(input_devs),
               f"{len(input_devs)} input device(s): {[d['name'][:25] for d in input_devs[:3]]}")
    except Exception as exc:
        record("Audio", "sounddevice query", False, str(exc))

# ──────────────────────────────────────────────────
# TEST 10: n8n webhook reachability
# ──────────────────────────────────────────────────
def test_n8n():
    section("PHASE 10 · n8n Workflow Integration")
    try:
        import config
        url = config.N8N_WEBHOOK_URL
        if "your-n8n" in url or "localhost" in url:
            record("n8n", "Webhook URL configured", False, "Default placeholder URL – add real URL to .env")
            return
        t0 = time.monotonic()
        resp = requests.post(url, json={"source": "jarvis_test", "command": "ping"}, timeout=8)
        latency = (time.monotonic() - t0) * 1000
        record("n8n", "Webhook POST reachable", resp.status_code in (200, 201, 204),
               f"HTTP {resp.status_code}", latency_ms=latency)
    except requests.exceptions.ConnectionError:
        record("n8n", "Webhook POST reachable", False, "Connection refused – activate your n8n workflow")
    except Exception as exc:
        record("n8n", "Webhook POST reachable", False, str(exc))

# ──────────────────────────────────────────────────
# TEST 11: Asset files
# ──────────────────────────────────────────────────
def test_assets():
    section("PHASE 11 · Asset Integrity")
    assets = [
        ("assets/sounds/startup.mp3",   "Startup sound"),
        ("assets/memory",               "Vision memory dir"),
        ("memory",                      "Memory directory"),
    ]
    for path, label in assets:
        exists = Path(path).exists()
        record("Assets", f"{label} ({path})", exists,
               "OK" if exists else "Missing (non-critical – Jarvis will log warning)")

# ──────────────────────────────────────────────────
# TEST 12: End-to-end route→execute simulation
# ──────────────────────────────────────────────────
def test_e2e():
    section("PHASE 12 · End-to-End Command Simulation (No UI)")
    try:
        from core.command_router import route_command
        from core.action_registry import execute_action

        commands = [
            ("list files on desktop", None),   # Router handles directly
            ("play music",            None),
        ]
        for cmd, _ in commands:
            t0 = time.monotonic()
            routed = route_command(cmd)
            action = routed.get("action", "unknown")
            target = routed.get("target", "")
            if action != "unknown":
                result = execute_action(action, target, {})
                latency = (time.monotonic() - t0) * 1000
                record("E2E", f"'{cmd}'", result.get("success", False),
                       result.get("message", "")[:80], latency_ms=latency)
            else:
                latency = (time.monotonic() - t0) * 1000
                record("E2E", f"'{cmd}'", False, "Routed to AI fallback (expected for complex commands)",
                       latency_ms=latency)
    except Exception as exc:
        record("E2E", "E2E simulation", False, str(exc))

# ──────────────────────────────────────────────────
# FINAL REPORT CARD
# ──────────────────────────────────────────────────
def print_report():
    total   = len(RESULTS)
    passed  = sum(1 for r in RESULTS if r["passed"])
    failed  = total - passed
    pct     = (passed / total * 100) if total else 0

    # Grade
    if pct >= 90:   grade, colour = "A  — Production Ready 🚀",  GREEN
    elif pct >= 75: grade, colour = "B  — Mostly Ready ✅",       CYAN
    elif pct >= 60: grade, colour = "C  — Needs Attention ⚠️",   YELLOW
    else:           grade, colour = "D  — Requires Setup 🔧",     RED

    ai_latencies = [r["latency_ms"] for r in RESULTS
                    if r["category"] == "AI" and r["latency_ms"] is not None]
    avg_ai = sum(ai_latencies) / len(ai_latencies) if ai_latencies else 0

    print(f"\n{BOLD}{'═'*55}{RESET}")
    print(f"{BOLD}  JARVIS-X DEXTER COPILOT — SYSTEM REPORT CARD{RESET}")
    print(f"{'═'*55}")
    print(f"  Tests passed   : {GREEN}{passed}{RESET} / {total}")
    print(f"  Tests failed   : {RED}{failed}{RESET}")
    print(f"  Score          : {colour}{pct:.1f}%{RESET}")
    print(f"  Grade          : {colour}{grade}{RESET}")
    print(f"  Avg AI Latency : {CYAN}{avg_ai:.0f}ms{RESET}")
    print(f"{'─'*55}")

    # Failures summary
    failures = [r for r in RESULTS if not r["passed"]]
    if failures:
        print(f"\n{BOLD}  ⚠  Manual Action Required:{RESET}")
        for r in failures:
            print(f"  • [{r['category']}] {r['test']}")
            if r["detail"]:
                print(f"      → {r['detail']}")

    # Save JSON report
    report_dir = Path(__file__).resolve().parent / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "jarvis_test_report.json"
    with open(report_path, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "score_pct": pct,
            "grade": grade,
            "avg_ai_latency_ms": avg_ai,
            "total": total, "passed": passed, "failed": failed,
            "results": RESULTS
        }, f, indent=2)
    print(f"\n  📄 Full report saved → {report_path}")
    print(f"{'═'*55}\n")

# ──────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"\n{BOLD}{CYAN}🤖 JARVIS-X AUTOMATION TEST SUITE{RESET}")
    print(f"{CYAN}   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}\n")

    test_config()
    test_ollama()
    test_router()
    test_memory()
    test_eventbus()
    test_vosk()
    test_microphone()
    test_n8n()
    test_assets()
    test_executor()
    test_e2e()
    test_ai_engine()   # last — heaviest (AI latency)

    print_report()
