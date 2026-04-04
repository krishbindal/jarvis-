"""
JARVIS-X Phase 26: Plugin/Skill System

Auto-discovers and registers skill modules from the /skills/ directory.
Each skill is a .py file that exposes:
  - SKILL_NAME: str — unique identifier
  - SKILL_PATTERNS: list[str] — regex patterns to match commands
  - SKILL_DESCRIPTION: str — human-readable description
  - execute(target: str, extra: dict) -> dict — the handler function
"""

from __future__ import annotations

import importlib
import os
import re
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from utils.logger import get_logger

logger = get_logger(__name__)

SKILLS_DIR = Path(__file__).parent
_loaded_skills: Dict[str, Dict[str, Any]] = {}


def discover_skills() -> Dict[str, Dict[str, Any]]:
    """Scan the skills directory and load all valid skill modules."""
    global _loaded_skills
    _loaded_skills.clear()

    skills_path = SKILLS_DIR
    if not skills_path.exists():
        logger.warning("[SKILLS] Skills directory not found: %s", skills_path)
        return _loaded_skills

    # Ensure skills dir is in path
    str_path = str(skills_path.parent)
    if str_path not in sys.path:
        sys.path.insert(0, str_path)

    for file in sorted(skills_path.glob("*.py")):
        if file.name.startswith("_") or file.name == "loader.py":
            continue

        module_name = f"skills.{file.stem}"
        try:
            mod = importlib.import_module(module_name)

            # Validate required attributes
            name = getattr(mod, "SKILL_NAME", None)
            patterns = getattr(mod, "SKILL_PATTERNS", None)
            execute_fn = getattr(mod, "execute", None)

            if not all([name, patterns, execute_fn]):
                logger.debug("[SKILLS] Skipping %s — missing required attributes", file.name)
                continue

            _loaded_skills[name] = {
                "name": name,
                "patterns": [re.compile(p, re.IGNORECASE) for p in patterns],
                "description": getattr(mod, "SKILL_DESCRIPTION", "No description"),
                "execute": execute_fn,
                "source": str(file),
            }
            logger.info("[SKILLS] Loaded skill: %s (%s)", name, file.name)

        except Exception as e:
            logger.error("[SKILLS] Failed to load %s: %s", file.name, e)

    logger.info("[SKILLS] Total skills loaded: %d", len(_loaded_skills))
    return _loaded_skills


def match_skill(text: str) -> Optional[Dict[str, Any]]:
    """Try to match input text against loaded skill patterns."""
    for skill_name, skill in _loaded_skills.items():
        for pattern in skill["patterns"]:
            match = pattern.search(text)
            if match:
                return {
                    "skill_name": skill_name,
                    "match": match,
                    "execute": skill["execute"],
                    "description": skill["description"],
                }
    return None


def execute_skill(skill_name: str, target: str, extra: Optional[Dict] = None) -> Dict[str, Any]:
    """Execute a loaded skill by name."""
    skill = _loaded_skills.get(skill_name)
    if not skill:
        return {"success": False, "status": "error", "message": f"Skill not found: {skill_name}"}

    try:
        return skill["execute"](target, extra or {})
    except Exception as e:
        logger.error("[SKILLS] Execution failed for %s: %s", skill_name, e)
        return {"success": False, "status": "error", "message": f"Skill error: {e}"}


def list_skills() -> List[Dict[str, str]]:
    """Return a list of all loaded skills with their descriptions."""
    return [
        {"name": s["name"], "description": s["description"], "source": s["source"]}
        for s in _loaded_skills.values()
    ]


# Auto-discover on import
discover_skills()
