"""Opt-in Python runner. Isolated cwd and filtered env, NOT an OS sandbox."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any, Dict

# Only OS plumbing is inherited, not provider keys, tokens or passwords.
_SAFE_ENV_KEYS = (
    "PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC",
    "TEMP", "TMP", "HOME", "USERPROFILE",
)


def _child_environment() -> Dict[str, str]:
    environment = {k: os.environ[k] for k in _SAFE_ENV_KEYS if k in os.environ}
    environment["PYTHONIOENCODING"] = "utf-8"
    environment["PYTHONNOUSERSITE"] = "1"
    return environment


def run_python_code(code: str) -> Dict[str, Any]:
    """Run user-approved opt-in code in a temporary directory.

    WARNING: this is not a security sandbox. The subprocess can access all
    files, network interfaces and permissions available to the parent user.
    Never enable for untrusted or model-generated code without independent approval.
    """
    from config import ALLOW_CODE_EXECUTION

    if not ALLOW_CODE_EXECUTION:
        return {
            "success": False,
            "status": "disabled",
            "message": "Python execution is disabled. Set JARVIS_ALLOW_CODE_EXECUTION=1 only if you trust the code.",
        }
    if not isinstance(code, str) or len(code) > 20000:
        return {"success": False, "status": "error", "message": "Python source must be text under 20,000 characters."}

    try:
        # Per-call directories prevent concurrent command collisions.
        with tempfile.TemporaryDirectory(prefix="jarvis_exec_") as folder:
            script = Path(folder) / "script.py"
            script.write_text(code, encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, "-I", str(script)],
                cwd=folder,
                env=_child_environment(),
                capture_output=True,
                text=True,
                timeout=30,
                encoding="utf-8",
                errors="replace",
            )
            stdout = completed.stdout.strip()[:16000]
            stderr = completed.stderr.strip()[:16000]
            if completed.returncode == 0:
                return {
                    "success": True,
                    "status": "success",
                    "message": "Code executed in a temporary working directory (not a security sandbox).",
                    "output": stdout or "(no output)",
                }
            return {
                "success": False,
                "status": "error",
                "message": f"Script exited with code {completed.returncode}",
                "output": stderr or stdout or "(no output)",
            }
    except subprocess.TimeoutExpired:
        return {"success": False, "status": "error", "message": "Script timed out after 30 seconds."}
    except Exception as exc:
        return {"success": False, "status": "error", "message": str(exc)}
