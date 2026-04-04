"""
JARVIS-X Phase 26: Deep Research Agent
An autonomous agent that performs multi-step web and local searches to synthesize complex reports.
"""

import time
from typing import List, Dict, Any
from utils.logger import get_logger
from brain.ai_engine import query_ai

logger = get_logger(__name__)

class DeepResearchAgent:
    """Specialized agent for high-complexity research tasks."""

    def __init__(self, event_bus):
        self._events = event_bus

    def perform_research(self, topic: str, max_steps: int = 3) -> str:
        """Perform recursive research on a topic."""
        logger.info(f"[RESEARCH] Initiating deep-dive on: {topic}")
        self._events.emit("proactive_warning", f"Sir, I am initiating a deep research cycle on {topic}. This may take a moment.")
        
        findings = []
        current_query = topic

        for step in range(1, max_steps + 1):
            logger.info(f"[RESEARCH] Step {step}/{max_steps}: {current_query}")
            
            # 1. Use existing search/query tools (simulated here since we are in brain)
            # In a real app, this would trigger the actual search skill
            search_prompt = f"Search the web for {current_query} and provide a detailed summary of findings."
            result = query_ai(search_prompt, system_msg="You are a research assistant. Provide factual, detailed data.")
            
            findings.append(f"### Phase {step}: {current_query}\n{result}")
            
            # 2. Ask AI what the next logical question is based on these findings
            next_step_prompt = f"Based on these findings about '{topic}', what is the single most important follow-up question to research next?\nFindings: {result}\nRespond ONLY with the question."
            next_q = query_ai(next_step_prompt).strip()
            
            if not next_q or next_q.lower() in current_query.lower():
                break
            current_query = next_q
            time.sleep(1) # Polite delay

        # 3. Final Synthesis
        synthesis_prompt = f"Synthesize a comprehensive, professional report on '{topic}' based on the following multi-phase research:\n\n" + "\n\n".join(findings)
        report = query_ai(synthesis_prompt, system_msg="You are Jarvis. Synthesize a professional briefing. Be thorough and polite.")
        
        logger.info("[RESEARCH] Deep research complete.")
        return report
