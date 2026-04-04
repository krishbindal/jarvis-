from __future__ import annotations

"""Lightweight intent detection and routing prior to AI."""

from dataclasses import dataclass
from typing import Any, Dict, Optional

import config
from core.command_router import route_command
from memory.workflow_store import resolve_macro
from skills import skill_registry
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class IntentDecision:
    route: str
    confidence: float
    payload: Dict[str, Any]
    needs_confirmation: bool = False
    source: str = "rule"


def _normalize(text: str) -> str:
    cleaned = text.lower().strip()
    for stop in ("please",):
        cleaned = cleaned.replace(stop, "").strip()
    return cleaned


def strip_wake_word(text: str) -> tuple[str, bool]:
    normalized = text.lower().strip()
    wake = config.WAKE_WORD.lower()
    if normalized.startswith(wake):
        remainder = normalized[len(wake):].strip(",. ")
        return remainder or normalized, True
    return normalized, False


def _estimate_complexity(text: str) -> float:
    tokens = text.split()
    token_count = len(tokens)
    has_question = any(tok.endswith("?") for tok in tokens) or "how" in tokens or "why" in tokens
    has_multi = "and" in tokens or "then" in tokens or "," in text
    score = 0.1 + min(token_count / 20, 0.5)
    if has_question:
        score += 0.2
    if has_multi:
        score += 0.1
    return min(score, 1.0)


def detect_intent(command: str, context: Optional[Dict[str, Any]] = None) -> IntentDecision:
    context = context or {}
    normalized = _normalize(command)

    macro_steps = resolve_macro(normalized)
    if macro_steps:
        logger.info("[ROUTER] Macro matched: %s", normalized)
        return IntentDecision(route="macro", confidence=0.95, payload={"steps": macro_steps}, source="macro")

    skill_registry.load()
    skill = skill_registry.match(normalized)
    if skill:
        logger.info("[ROUTER] Skill matched: %s", skill.name)
        return IntentDecision(route="skill", confidence=0.9, payload={"skill": skill}, source="skill")

    routed = route_command(normalized)
    if routed.get("action") != "unknown":
        logger.info("[ROUTER] Rule matched: %s", routed.get("action"))
        return IntentDecision(route="rule", confidence=0.8, payload={"route_result": routed}, source="rule")

    complexity = _estimate_complexity(normalized)
    needs_confirmation = complexity < config.INTENT_CONFIDENCE_THRESHOLD
    return IntentDecision(
        route="ai",
        confidence=max(complexity, 0.4),
        payload={"route_result": routed},
        needs_confirmation=needs_confirmation,
        source="ai",
    )
