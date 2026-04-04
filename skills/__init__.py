from __future__ import annotations

"""Skill package exposing a shared registry."""

from skills.loader import SkillRegistry

skill_registry = SkillRegistry()
__all__ = ["SkillRegistry", "skill_registry"]
