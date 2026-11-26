"""Evidence-only, non-invasive Jarvis setup and readiness observations.

No claim of production readiness can be made from package presence, environment
variables or a local port check. No cloud audio, browser, or desktop actions run.
"""
from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import platform
import sqlite3
import subprocess
import sys
from typing import Any
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def _module_present(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


def _git_commit(root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=3, check=True,
        )
        commit = result.stdout.strip()
        return commit if len(commit) == 40 and all(c in "0123456789abcdef" for c in commit.lower()) else None
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def _db_schema(db: Path) -> dict[str, Any]:
    if not db.is_file():
        return {
            "name": "Local memory database",
            "status": "not_tested",
            "detail": "Database file not present; did not create or modify it.",
        }
    try:
        # SQLite mode=ro guarantees that a diagnostic cannot create a database.
        connection = sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True, timeout=2)
        try:
            names = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        finally:
            connection.close()
        if "interactions" in names:
            return {
                "name": "Local memory database",
                "status": "observed",
                "detail": "Read-only inspection found an interactions table; writes and recall were NOT tested.",
            }
        return {
            "name": "Local memory database",
            "status": "unavailable",
            "detail": "SQLite file opened, but expected interactions table was not present.",
        }
    except (sqlite3.DatabaseError, OSError, ValueError) as exc:
        return {
            "name": "Local memory database",
            "status": "unavailable",
            "detail": f"Read-only database inspection failed ({type(exc).__name__}).",
        }


def collect_evidence(
    root: Path | None = None,
    *,
    environment: dict[str, str] | None = None,
    probe_ollama: bool = False,
) -> dict[str, Any]:
    """Return actual, scoped facts; no side effects, cloud keys or fake scores."""
    root = (root or ROOT).resolve()
    env = environment if environment is not None else os.environ
    checks: list[dict[str, Any]] = []

    checks.append({
        "name": "Python runtime",
        "status": "observed" if sys.version_info[:2] == (3, 11) else "unavailable",
        "detail": f"Running Python {platform.python_version()}; tested project target is 3.11.",
    })
    checks.append({
        "name": "Operating system",
        "status": "observed" if os.name == "nt" else "not_tested",
        "detail": (
            f"Actual host: {platform.system()} {platform.release()}. "
            "Windows features cannot be verified on a non-Windows host."
        ),
    })
    for module in ("PySide6", "sounddevice", "vosk", "requests", "psutil"):
        present = _module_present(module)
        checks.append({
            "name": f"Module import path: {module}",
            "status": "observed" if present else "unavailable",
            "detail": (
                "Python import path found; no GUI/audio runtime test was performed."
                if present else "Python import path not found in this environment."
            ),
        })

    model_string = env.get("VOICE_MODEL_PATH", "voice/model")
    model_path = Path(model_string).expanduser()
    if not model_path.is_absolute():
        model_path = root / model_path
    model_exists = model_path.is_dir()
    checks.append({
        "name": "Vosk model folder",
        "status": "observed" if model_exists else "unavailable",
        "detail": (
            "Configured directory exists; loading and recognition have NOT been tested."
            if model_exists else "Configured model directory is missing."
        ),
    })
    for provider, key in (("Groq", "GROQ_API_KEY"), ("Gemini", "GEMINI_API_KEY")):
        configured = bool(env.get(key, "").strip())
        checks.append({
            "name": f"{provider} credential",
            "status": "not_tested",
            "detail": (
                "Key configured; validity, quota and actual API response NOT checked."
                if configured else "No key present in process environment; .env file not inspected; live provider not checked."
            ),
        })

    if probe_ollama:
        try:
            with urlopen("http://127.0.0.1:11434/api/tags", timeout=2) as response:
                status = response.status
            checks.append({
                "name": "Ollama local HTTP endpoint",
                "status": "observed" if status == 200 else "unavailable",
                "detail": (
                    f"GET /api/tags returned HTTP {status}; generation/model readiness NOT tested."
                ),
            })
        except (OSError, ValueError) as exc:
            checks.append({
                "name": "Ollama local HTTP endpoint",
                "status": "unavailable",
                "detail": f"Local endpoint probe failed ({type(exc).__name__}); no model generation tested.",
            })
    else:
        checks.append({
            "name": "Ollama local HTTP endpoint",
            "status": "not_tested",
            "detail": "Not probed by default. Enable --probe-ollama for a local HTTP check.",
        })
    checks.append(_db_schema(root / "memory" / "jarvis.db"))

    for feature in (
        "Physical microphone and wake recognition",
        "Speaker and text-to-speech playback",
        "Cloud AI real responses and tool accuracy",
        "Windows desktop actions and user approvals",
        "Thirty-minute load, shutdown and resource recovery",
    ):
        checks.append({
            "name": feature,
            "status": "not_tested",
            "detail": "Requires separate, logged acceptance test on the actual Windows machine.",
        })

    counts = {status: sum(c["status"] == status for c in checks) for status in ("observed", "unavailable", "not_tested")}
    return {
        "kind": "non_invasive_readiness_evidence",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "commit": _git_commit(root),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "release_ready": False,
        "release_status": "NOT_VERIFIED",
        "scope": "Local static/availability checks only; no automatic cloud or device validation.",
        "counts": counts,
        "checks": checks,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# JARVIS-X: evidence-based readiness report",
        "",
        f"**Generated (UTC):** {report['generated_utc']}",
        f"**Git commit:** {report.get('commit') or 'unknown'}",
        f"**Host:** {report['platform']} · Python {report['python']}",
        "",
        "**Release status: NOT VERIFIED** — this report cannot certify full functionality.",
        "",
        "| Observation | Status | Evidence and limits |",
        "| --- | --- | --- |",
    ]
    for check in report["checks"]:
        detail = check["detail"].replace("|", "/").replace("\n", " ")
        lines.append(f"| {check['name']} | {check['status']} | {detail} |")
    lines.extend([
        "",
        "A configured API key does not prove a provider is online. Import paths do not prove hardware works.",
        "No actions, email delivery, microphone recordings, or cloud requests were performed.",
        "Complete docs/RELEASE_READINESS.md and preserve actual test logs before assigning a release rating.",
        "",
    ])
    return "\n".join(lines)


def write_report(report: dict[str, Any], destination: Path) -> tuple[Path, Path]:
    """Create a fresh JSON+Markdown report; do not overwrite a historical source file."""
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    output_json = destination / "readiness-evidence.json"
    output_md = destination / "READINESS_REPORT.md"
    output_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    output_md.write_text(render_markdown(report), encoding="utf-8")
    return output_json, output_md
