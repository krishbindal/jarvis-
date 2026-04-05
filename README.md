# JARVIS-X (Phase 1)

Local, offline-first desktop assistant scaffolded for Windows using Python, PySide6, and Ollama (later phases). This repository currently delivers Phase 1: activation trigger, cinematic startup, and a styled UI shell.

## Universal Desktop Automation
- Natural-language → structured intent planner that emits `{goal, steps[]}` without hardcoded app/site flows.
- Task planner maps steps to generic actions (`open_app`, `open_url`, `search`, `click`, `type`, `scroll`, `download`) and reuses current app/browser context.
- Universal executor drives pyautogui/Playwright to click/type/scroll, opens URLs with existing browsers, and handles downloads with safety checks.
- Continuous context tracking keeps follow-up commands in the same surface (e.g., “open chrome” → “search python tutorial” stays in Chrome).
- Step-level feedback logs every action and stops on failures with a concise status message.

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

Key packages: `PySide6`, `sounddevice`, `numpy`, `pygame`, `vosk` (offline ASR).

## Running
Ensure a microphone is available, then:

```bash
python main.py
```

- Wait for a **double clap** to trigger startup.
- The startup MP3 (`assets/sounds/startup.mp3`) plays with pygame, then the PySide6 HUD opens. If the file is missing, the app will continue without audio.
- After wake, Jarvis briefly listens for a voice command using Vosk (offline). Place a model at `voice/model` (or set `VOICE_MODEL_PATH` in `config.py`). If nothing is captured, just type in the UI as before.
- The UI now uses a dark Jarvis HUD with neon accents, a circular animation, command log panel, and status banner.
- Commands typed into the UI emit `command_received` events; the core routes them and emits `command_result` back to the log.

## Real-Time Experience
- Immediate acknowledgements: Jarvis answers with a short verbal cue as soon as a command arrives (voice or text) and starts streaming a "thinking" narration token-by-token from your local Ollama model (fallback to Groq).
- Speak -> Act -> Stream: Actions begin right away with mid-action voice lines (e.g., "Opening Chrome") and a continuous status feed to the overlay and console typewriter.
- Interrupts: Say “stop” at any time to halt speech/streams via the event bus.
- Cinematic console: System logs and streamed tokens render with a lightweight typewriter effect; the floating overlay mirrors command progress stages.
- Context-aware agent loop: A shared session context (current app/url, last intent/action) feeds a planner that can continue follow-up commands on any app or site without hardcoded flows.

If you want to bypass clap activation (e.g., during development), instantiate `JarvisApp(auto_start=True)` in `main.py`.

## Customizing the Startup Sound
Place your track at `assets/sounds/startup.mp3`. Playback is blocking to keep the cinematic sequence intact.

## Notes
- Clap detection uses an amplitude threshold; if your environment is noisy, tune `clap_threshold`, `max_gap_s`, and `cooldown_s` in `triggers/clap_detector.py`.
- The detector now auto-calibrates ambient noise for the first two seconds, looks for two distinct peaks 0.5–1.0s apart, ignores continuous noise, and enforces a ~2.5s cooldown after a trigger.
- Future phases will fill `brain/`, `executor/`, and `memory/` with AI, automation, and persistence modules.
