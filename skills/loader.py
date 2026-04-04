from __future__ import annotations

"""Dynamic skill loader and matcher."""

import importlib
import pkgutil
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SkillModule:
    name: str
    triggers: List[str]
    runner: Callable[[str, Dict[str, Any]], Dict[str, Any]]
    description: str = ""


class SkillRegistry:
    def __init__(self) -> None:
        self._skills: Dict[str, SkillModule] = {}
        self._loaded = False

    def load(self) -> None:
        if self._loaded:
            return
        package_name = __name__.rsplit(".", 1)[0]
        package = importlib.import_module(package_name)
        for modinfo in pkgutil.iter_modules(package.__path__):  # type: ignore[attr-defined]
            mod_name = modinfo.name
            if mod_name.startswith("_") or mod_name == "loader":
                continue
            full_name = f"{package_name}.{mod_name}"
            try:
                module = importlib.import_module(full_name)
                runner = getattr(module, "run", None)
                triggers = getattr(module, "TRIGGERS", [])
                name = getattr(module, "NAME", mod_name)
                desc = getattr(module, "DESCRIPTION", "")
                if callable(runner) and triggers:
                    self._skills[name] = SkillModule(name=name, triggers=[t.lower() for t in triggers], runner=runner, description=desc)
            except Exception as exc:  # noqa: BLE001
                logger.error("Failed to load skill %s: %s", full_name, exc)
        self._loaded = True
        logger.info("[SKILL] Loaded %d skills", len(self._skills))

    def match(self, command: str) -> Optional[SkillModule]:
        if not self._loaded:
            self.load()
        normalized = command.lower()
        for skill in self._skills.values():
            if any(trigger in normalized for trigger in skill.triggers):
                return skill
        return None

    def run(self, skill: SkillModule, command: str, context: Dict[str, Any]) -> Dict[str, Any]:
        try:
            return skill.runner(command, context)
        except Exception as exc:  # noqa: BLE001
            logger.error("[SKILL] %s failed: %s", skill.name, exc)
            return {"success": False, "status": "error", "message": f"Skill {skill.name} failed: {exc}"}

    def registry_snapshot(self) -> Dict[str, List[str]]:
        return {name: mod.triggers for name, mod in self._skills.items()}
