# JARVIS-X (Phase 1)

Local, offline-first desktop assistant scaffolded for Windows using Python, PySide6, and Ollama (later phases). This repository currently delivers Phase 1: activation trigger, cinematic startup, and a styled UI shell.

## Folder Structure
- `core/` – application orchestration and startup sequence
- `triggers/` – activation inputs (double-clap detector)
- `ui/` – PySide6 frontend
- `brain/` – AI reasoning (placeholder for later phases)
- `executor/` – tool execution (placeholder)
- `memory/` – storage layer (placeholder)
- `utils/` – shared helpers
- `main.py` – entrypoint
- `requirements.txt` – runtime dependencies

## Dependencies
Install with Python 3.10+:

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

Key packages: `PySide6`, `sounddevice`, `numpy`, `pygame`.

## Running
Ensure a microphone is available, then:

```bash
python main.py
```

- Wait for a **double clap** to trigger startup.
- The startup MP3 (`assets/sounds/startup.mp3`) plays with pygame, then the PySide6 HUD opens. If the file is missing, the app will continue without audio.

If you want to bypass clap activation (e.g., during development), instantiate `JarvisApp(auto_start=True)` in `main.py`.

## Customizing the Startup Sound
Place your track at `assets/sounds/startup.mp3`. Playback is blocking to keep the cinematic sequence intact.

## Notes
- Clap detection uses an amplitude threshold; if your environment is noisy, tune `clap_threshold`, `max_gap_s`, and `cooldown_s` in `triggers/clap_detector.py`.
- The detector now auto-calibrates ambient noise for the first two seconds, looks for two distinct peaks 0.5–1.0s apart, ignores continuous noise, and enforces a ~2.5s cooldown after a trigger.
- Future phases will fill `brain/`, `executor/`, and `memory/` with AI, automation, and persistence modules.
