# JARVIS-X — Windows desktop assistant

A Python 3.11 Windows desktop-assistant prototype combining PySide6 UI, offline Vosk speech recognition, optional cloud AI, local Ollama, desktop tools, persistent SQLite memory, and opt-in background services.

**Status:** Automated tests cover selected components; this is not a certified production release. Full microphone, speaker, model, and Windows automation behavior still needs local hardware testing.

## Universal Desktop Automation
- Natural-language → structured intent planner that emits `{goal, steps[]}` without hardcoded app/site flows.
- Task planner maps steps to generic actions (`open_app`, `open_url`, `search`, `click`, `type`, `scroll`, `download`) and reuses current app/browser context.
- Universal executor drives pyautogui/Playwright to click/type/scroll, opens URLs with existing browsers, and handles downloads with safety checks.
- Continuous context tracking keeps follow-up commands in the same surface (e.g., “open chrome” → “search python tutorial” stays in Chrome).
- Step-level feedback logs every action and stops on failures with a concise status message.

## Autonomous Intelligence
- Background Autonomy Engine observes active apps/time with low-CPU sampling to learn habits without spamming the user.
- Pattern detection persists common routines (e.g., Chrome → YouTube → Spotify) to SQLite with embeddings, then suggests them in a confident/minimal Jarvis tone.
- Context-aware suggestions avoid reopening active apps and pause while a task is running; user can interrupt via the event bus (`interrupt_autonomy`).
- Scheduler supports one-off or recurring commands with safe auto-execution and self-healing fallbacks (retries via `open_dynamic` when a launch fails).
- All observations, patterns, and schedules are stored in `memory/jarvis.db` for long-term learning.

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

## Installation (Windows, Python 3.11 x64)

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe main.py --doctor
.\.venv\Scripts\python.exe main.py
```

The UI opens immediately. To wait for a double clap, use `python main.py --wait-for-clap`. For voice, provision an English Vosk model in `voice/model`; to enable OpenWakeWord, provision a supported wake model separately. `TALK` activates voice capture when Vosk is present. The startup MP3 is optional and not included in this repository.

## AI configuration and privacy

- Groq and Gemini require API keys configured locally in `.env`; Ollama needs a running local server and model.
- Default Gemini model: `GEMINI_MODEL=gemini-3.5-flash`. The vision model defaults to the same ID; override with `JARVIS_VISION_MODEL`. Model availability and quotas depend on your account; verify using the official models API. No live cloud API test is performed by CI.
- Background screenshots, clipboard monitoring, file sorting, autonomy, and MCP subprocesses are disabled by default. Opt in only when you understand the data accessed.
- Cloud audio transcription may send microphone recordings to Groq when a key is present. Detailed offline/cloud privacy controls remain planned in issue #18.
- Model-generated code execution is disabled unless **both** `JARVIS_ALLOW_CODE_EXECUTION=1` and `JARVIS_ALLOW_MODEL_CODE_EXECUTION=1`. This is NOT a security sandbox; generated scripts still have your OS user permissions.
- Generated skill proposals are disabled by default (`JARVIS_ENABLE_SKILL_GENERATION=0`). If enabled, proposed Python is written only to `data/generated_skills_pending` for human review; it is never loaded automatically.
- Action-level permission dialogs, a centralized policy, and an emergency stop are still tracked in issue #17. Do not give Jarvis administrator privileges.

## What the automated tests actually check

GitHub Actions runs Python compilation, dependency installation, unit tests on Windows, and an optional MCP echo/subprocess integration test on Windows and Ubuntu. These tests do **not** validate a live microphone, speaker, actual AI API keys, real desktop interactions or performance on a specific laptop. Check the Actions page for the exact number of passing tests and skipped tests for your latest commit.

## Customizing the Startup Sound
Place your track at `assets/sounds/startup.mp3`. Playback is blocking to keep the cinematic sequence intact.

## Notes
- Clap detection uses an amplitude threshold; if your environment is noisy, tune `clap_threshold`, `max_gap_s`, and `cooldown_s` in `triggers/clap_detector.py`.
- The detector now auto-calibrates ambient noise for the first two seconds, looks for two distinct peaks 0.5–1.0s apart, ignores continuous noise, and enforces a ~2.5s cooldown after a trigger.
- Future phases will fill `brain/`, `executor/`, and `memory/` with AI, automation, and persistence modules.

## Windows reliability quick start

Use 64-bit Python 3.11. From the repository folder in PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe main.py --doctor
.\.venv\Scripts\python.exe main.py
```

Jarvis opens the desktop UI immediately so text commands work without a microphone. Run `python main.py --wait-for-clap` to wait for a double clap instead. Install a compatible English Vosk recognition model at `voice/model` (or set `VOICE_MODEL_PATH` in `.env`) for voice input. The **TALK** button offers manual voice activation when wake-word detection is unavailable. Some browser automation features additionally require `python -m playwright install chromium`.

Jarvis will **not register Windows startup automatically**. To opt in: `python main.py --install-autostart`. To remove that entry: `python main.py --remove-autostart`.

AI answers require a running Ollama instance with the `MODEL_NAME` model (default `llama3`), or an API key configured for a supported cloud provider. The UI and built-in commands can still be tested without those AI services.

Background vision, proactive/autonomous monitoring, file organization, knowledge indexing, the sentinel, system monitoring, and MCP subprocesses are **disabled by default**. Enable individual `JARVIS_ENABLE_*` flags in `.env` when you want the respective behavior. The file organizer automatically moves newly created files on Desktop/Downloads. Vision can send screenshots to cloud providers; use it only with explicit intent.

Use `python main.py --doctor` for a dependency and AI setup overview. Logs are in `assets/logs/jarvis.log`. Full microphone, speaker, graphical automation, and Windows integrations must be verified on a Windows PC.

### Voice reliability and model setup

The microphone callback now queues frames to a bounded worker; wake-word inference, Vosk and notifications run outside the real-time audio callback. Each TALK/wake event restarts the seven-second command window.

The conversational `WAKE_WORD` and the separately configured OpenWakeWord `WAKE_MODEL_NAME` (default `hey jarvis`) are different settings. Jarvis **does not download wake models on startup**. Provision them once, after installing requirements:

```powershell
.\.venv\Scripts\python.exe -c "import openwakeword; openwakeword.utils.download_models()"
```

Also install a Vosk English recognition model in the folder selected by `VOICE_MODEL_PATH` (default `voice/model`). Voice is unavailable until that Vosk model exists; the text UI can still be used. Run `python main.py --doctor` to inspect dependencies and configuration.

CI includes a Windows Python 3.11 dependency installation and unit-test job. It does not validate microphone hardware, wake-word accuracy, speakers, or actual desktop automation; test those on the target Windows machine before a release.

### Optional MCP integration and execution security

The MCP hub is **disabled by default**. Install its separate dependency only if needed:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-mcp.txt
```

Set `JARVIS_ENABLE_MCP_HUB=1` in your local `.env`, and review every enabled command in `config/mcp_servers.json` before starting Jarvis. MCP servers execute with the permissions of your Windows user account. The launcher filters inherited environment variables to avoid passing API keys by default, but any variables deliberately added in an MCP server's `env` configuration are available to that server.

**Dynamic Python execution is not a security sandbox.** `JARVIS_ALLOW_CODE_EXECUTION=0` is the default and should remain off unless you have reviewed and approved the code you will execute. Even when enabled, the separate temporary folder, `sys.executable -I`, and filtered environment do **not** restrict access to your files, network, or Windows permissions. Do not let an LLM autonomously execute untrusted code.

The local n8n notification server remains disabled until `N8N_NOTIFY_TOKEN` is set. When enabled, it authenticates incoming requests, binds to loopback by default, limits payload size, and uses bounded socket reads. For future centralized action approvals and an emergency stop, see [issue #17](https://github.com/krishbindal/jarvis-/issues/17).
