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

Key packages: `PySide6`, `sounddevice`, `numpy`.

## Running
Ensure a microphone is available, then:

```bash
python main.py
```

- Wait for a **double clap** to trigger startup.
- A rising tone plays (swap in any Iron Man theme locally if desired), then the PySide6 HUD opens.

If you want to bypass clap activation (e.g., during development), instantiate `JarvisApp(auto_start=True)` in `main.py`.

## Customizing the Startup Sound
Replace the generated tone in `core/startup.py` with a path-based player if you have a local track:

```python
# inside play_startup_sound
sd.play(soundfile.read("path/to/ironman_theme.wav")[0], samplerate=44100, blocking=True)
```

## Notes
- Clap detection uses an amplitude threshold; if your environment is noisy, tune `clap_threshold`, `max_gap_s`, and `cooldown_s` in `triggers/clap_detector.py`.
- Future phases will fill `brain/`, `executor/`, and `memory/` with AI, automation, and persistence modules.
