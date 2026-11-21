"""Dependency-first health check that can run without the GUI or audio stack."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import config


def _available(module: str) -> bool:
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError, ModuleNotFoundError):
        return False


def run_diagnostics() -> bool:
    """Print actionable checks and fail only for essential launch dependencies."""
    print("\n=== JARVIS-X SETUP DOCTOR ===")
    required = {
        "PySide6": "PySide6", "sounddevice": "sounddevice", "numpy": "numpy",
        "pygame": "pygame", "watchdog": "watchdog", "requests": "requests",
        "groq": "groq", "google.genai": "google-genai", "psutil": "psutil",
        "pyautogui": "pyautogui", "vosk": "vosk", "yt_dlp": "yt-dlp",
    }
    if os.name == "nt":
        required.update({"win32gui": "pywin32", "win32process": "pywin32"})
    failures = []
    for module, package in required.items():
        ok = _available(module)
        print(f"{'OK     ' if ok else 'MISSING'} {module}")
        if not ok:
            failures.append(package)

    if failures:
        print("\nInstall missing dependencies using:")
        print("  python -m pip install -r requirements.txt")
        print("Missing packages: " + ", ".join(sorted(set(failures))))

    model_path = Path(config.VOICE_MODEL_PATH).expanduser()
    if not model_path.is_absolute():
        model_path = Path(__file__).resolve().parent.parent / model_path
    if model_path.is_dir():
        print(f"OK      Vosk voice model: {model_path}")
    else:
        print(f"OPTIONAL Vosk model missing: {model_path} (text UI still works)")

    if config.GROQ_API_KEY or config.GEMINI_API_KEY:
        print("OK      Cloud AI credential configured")
    else:
        print("OPTIONAL No cloud AI keys; use local Ollama or set a key in .env")

    try:
        with urlopen("http://127.0.0.1:11434/api/tags", timeout=2) as response:
            if response.status == 200:
                print("OK      Ollama reachable")
            else:
                print(f"OPTIONAL Ollama returned HTTP {response.status}")
    except (OSError, URLError, TimeoutError):
        print("OPTIONAL Ollama not running; start it if using a local model")

    for label, enabled in (
        ("Cloud STT audio upload", config.ALLOW_CLOUD_STT),
        ("Cloud screen upload", config.ALLOW_CLOUD_VISION),
        ("Cloud clipboard analysis", config.ALLOW_CLOUD_CLIPBOARD),
        ("Clipboard persistence", config.REMEMBER_CLIPBOARD),
        ("Local screen snapshots", config.ALLOW_LOCAL_SCREEN_SNAPSHOTS),
    ):
        print(f"{'ENABLED ' if enabled else 'DISABLED'} {label}")

    if os.name != "nt":
        print("NOTE     Jarvis desktop automation is Windows-oriented")

    print("\n" + ("READY: essential Python modules available" if not failures else "NOT READY: resolve missing modules"))
    return not failures
