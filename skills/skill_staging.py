"""Staging area for model-generated skill proposals.

No candidate is imported, executed, or placed in the live skills package.
Review candidate code as a human before manually installing anything.
"""
from __future__ import annotations

import ast
from pathlib import Path
import re
from typing import Any, Dict

_NAME = re.compile(r"[a-z][a-z0-9_]{1,48}\Z")
DEFAULT_STAGING_DIR = Path(__file__).resolve().parents[1] / "data" / "generated_skills_pending"


def stage_skill_candidate(code: str, proposed_name: str, output_dir: Path | None = None) -> Dict[str, Any]:
    """Validate syntax/name and write a candidate, never importing it."""
    if not isinstance(code, str) or not code.strip() or len(code) > 20_000:
        return {"success": False, "status": "error", "message": "Candidate source must be 1–20,000 characters."}

    if not isinstance(proposed_name, str) or _NAME.fullmatch(proposed_name) is None:
        return {"success": False, "status": "error", "message": "Invalid skill name; use lowercase letters, digits and underscores."}

    try:
        parsed = ast.parse(code, filename=f"{proposed_name}.py")
    except SyntaxError as exc:
        return {"success": False, "status": "error", "message": f"Candidate has invalid Python syntax (line {exc.lineno})."}

    declared_names = [
        node.value.value for node in parsed.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "SKILL_NAME" for target in node.targets)
        and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)
    ]
    if declared_names != [proposed_name]:
        return {"success": False, "status": "error", "message": "Declared SKILL_NAME must match the proposed safe filename."}

    folder = Path(output_dir) if output_dir is not None else DEFAULT_STAGING_DIR
    folder.mkdir(parents=True, exist_ok=True)
    candidate = folder / f"{proposed_name}.py"
    try:
        with candidate.open("x", encoding="utf-8") as stream:
            stream.write(code)
    except FileExistsError:
        return {"success": False, "status": "error", "message": "A candidate with that name already exists; review it before replacing."}
    return {
        "success": True,
        "status": "pending_review",
        "message": f"Staged {proposed_name}.py for manual code review. It has NOT been installed or executed.",
        "output": {"filename": candidate.name, "path": str(candidate)},
    }
