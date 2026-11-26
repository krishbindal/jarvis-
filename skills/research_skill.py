"""A limited, source-backed research lookup — no fabricated web results."""
from __future__ import annotations

from typing import Any, Dict

from brain.researcher import DeepResearchAgent
from utils.events import EventBus

SKILL_NAME = "deep_research"
SKILL_DESCRIPTION = "Fetch cited encyclopedia excerpts, not comprehensive web research."
SKILL_PATTERNS = [
    r"deep(?:[- ])research (.+)",
    r"thoroughly research (.+)",
    r"investigate (.+)",
    r"provide (?:a )?full report on (.+)",
]


def execute(target: str, extra: Dict[str, Any] = None) -> Dict[str, Any]:
    """Fail closed without sources; explicitly label the limited coverage."""
    options = extra if isinstance(extra, dict) else {}
    topic = target or options.get("topic", "")
    if not isinstance(topic, str) or not topic.strip():
        return {
            "success": False,
            "status": "invalid_topic",
            "message": "Please provide a research topic.",
        }
    researcher = DeepResearchAgent(event_bus=EventBus())
    report = researcher.perform_research(topic.strip())
    if researcher.source_count == 0:
        return {
            "success": False,
            "status": "no_verified_sources",
            "message": report,
            "output": report,
        }
    return {
        "success": True,
        "status": "sourced_excerpt_retrieval",
        "message": (
            f"Retrieved {researcher.source_count} cited encyclopedia excerpts. "
            "This is not a comprehensive web search or independently verified report."
        ),
        "output": report,
        "source_count": researcher.source_count,
    }
