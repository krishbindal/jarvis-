# JARVIS-X release evidence checklist

## What counts as verified

- **CI compilation and unit tests:** Read the latest GitHub Actions run for the exact commit. Report the actual `Ran N tests`, failures and skips from job logs.
- **Dependency consistency:** The Windows workflow installs the 23 direct packages constrained by `constraints-win311.txt` (versions observed in a successful real Windows CI run) and runs `pip check`. This is **not** a complete transitive lockfile. The workflow uploads the complete `pip freeze --all` output for the actual tested machine.
- **Headless UI:** CI constructs the PySide6 main window/overlay under the offscreen Qt platform and uploads timing plus process RSS measurements to `artifacts/headless_qt_benchmark.json`. These are measurements **of the GitHub runner**, not of a user laptop or real desktop.
- **MCP:** The separate workflow runs a real local echo MCP server roundtrip on Windows and Ubuntu. Other MCP providers are not tested in this workflow.

## Manual Windows acceptance test (complete with real measured results)

Keep original logs and the exact git commit SHA. No estimated or generated pass counts.

- [ ] Clean Windows 10/11 64-bit with Python 3.11. Capture OS build, CPU, memory and Python version
- [ ] `python -m pip install -r requirements.txt -c constraints-win311.txt` completes and `python -m pip check` passes
- [ ] `python main.py --doctor` reports the installed assets / provider readiness
- [ ] Run 10 actual launch/close cycles; collect average, p50/p95 latency, runtime process count and leftover microphone/port locks
- [ ] Type a command, receive a result, and close the Qt main window without orphan assistant processes
- [ ] Provision and verify an English Vosk model; test TALK input and repeat after idle/sleep
- [ ] Provision OpenWakeWord models; test actual activation precision and false-trigger behavior
- [ ] Test speaker TTS with the intended laptop audio output and interruption
- [ ] With real credentials and explicit opt-ins, test Groq, Gemini and Ollama independently; record response/error details without including secrets
- [ ] Test read-only desktop actions followed by user-confirmed filesystem/communication actions
- [ ] Test approval denial, timeout, cancel and UI shutdown under concurrent requests
- [ ] Test clipboard, vision and cloud STT opt-ins with private-data canaries; confirm nothing is uploaded with opt-ins off
- [ ] Test application on multiple monitor DPI layouts and during network loss
- [ ] Perform a 30-minute voice/audio soak, capturing observed queue drops and system memory from the actual device
- [ ] Verify no API keys, email passwords, screenshots or private transcripts appear in published artifacts and CI logs

## Release threshold

Do **not** call the project 9/10, production-ready, reliable in every environment, or fully functional merely because CI is green. Require the hardware checklist, review of remaining P1 security/privacy issues, and a measured acceptance report. Any unchecked item stays explicitly **not verified**.

## Version provenance

The direct dependency pins were extracted from the `Successfully installed` record of the successful Windows CI run [44939263779](https://github.com/krishbindal/jarvis-/actions/runs/44939263779) at commit `3aef16dfe1a45f1aa0771cfc93405801653435b7`. The new workflow re-tests the pinned environment and captures the full resolved list in a build artifact.
