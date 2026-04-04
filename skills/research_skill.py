"""
JARVIS-X Phase 26: Omniscient Research
Skill to perform deep, multi-step research on complex topics.
"""

from typing import Dict, Any
from brain.researcher import DeepResearchAgent
# Local import in execute() will handle the EventBus

SKILL_NAME = "deep_research"
SKILL_DESCRIPTION = "Perform multi-step deep research on a specified topic."
SKILL_PATTERNS = [
    r"deep(?:[- ])research (.+)",
    r"thoroughly research (.+)",
    r"investigate (.+)",
    r"provide (?:a )?full report on (.+)"
]

def execute(target: str, extra: Dict[str, Any]) -> Dict[str, Any]:
    """Execute the deep research loop."""
    try:
        from utils import EventBus
        bus = EventBus() # Local bus if global not easily available
        researcher = DeepResearchAgent(event_bus=bus)
        
        # Target from regex is the topic
        topic = target or extra.get("topic", "unspecified topic")
        
        report = researcher.perform_research(topic)
        
        return {
            "success": True,
            "status": "success",
            "message": f"Sir, I have completed my deep dive into '{topic}'. Here is the briefing.",
            "output": report
        }
    except Exception as e:
        return {
            "success": False,
            "status": "error",
            "message": f"Sir, the research cycle failed: {e}"
        }
