from __future__ import annotations

"""AI engine using Ollama as a fallback command interpreter."""

import json
import base64
import os
from typing import Any, Dict, Iterable

import requests
import google.generativeai as genai
from groq import Groq

from utils.logger import get_logger
from config import MODEL_NAME, GEMINI_API_KEY, GROQ_API_KEY
from utils.system_context import get_system_stats
from core.mcp_hub import get_mcp_hub
from brain.providers import registry

OLLAMA_URL = "http://localhost:11434/api/generate"
logger = get_logger(__name__)

SYSTEM_PROMPT = """
You are Jarvis, a high-end, proactive 'Dexter Copilot' style agent. 
You are a professional teammate, not just a tool. Your personality should be reminiscent of JARVIS from Iron Man: sophisticated, capable, and sometimes subtly witty.

Available tools:
* list_files, create_folder, delete_file, move_file, copy_file, rename_file, search_file, file_info: File system management.
* download_file, download_video, convert_to_mp3, convert_to_pdf: Media / Web utilities.
* trigger_n8n: Advanced automation hub. Routes to specialized API integrations:
    - "news": Top tech headlines from Hacker News.
    - "weather": Current weather conditions.
    - "crypto": Live Bitcoin price from CoinDesk.
    - "joke": Random programming/misc joke.
    - "fact": Random fun fact.
    - "research": Deep web research via DuckDuckGo. Pass query in "target".
    - "quote": Random motivational/inspirational quote.
    - "define": Dictionary definition. Pass word in "target".
    Example: {"action": "trigger_n8n", "target": "research", "extra": {"query": "quantum computing"}}
    Example: {"action": "trigger_n8n", "target": "define", "extra": {"query": "serendipity"}}
* skill:browser: Use this for autonomous web automation via Playwright. Examples: "search google for React", "go to youtube.com", "read this article". Target should be the instruction. (Format: {"action": "skill:browser", "target": "search google for..."}).
* open_app: STRICTLY for opening installed LOCAL Desktop applications by name (e.g. "chrome", "notepad"). DO NOT use for websites like "youtube" or "netflix" - use open_url or skill:browser instead.
* kill_process: Close applications by name (e.g. "chrome", "spotify").
* open_url, media_control, power_state: Web/Media/System control.
* capture_screen: Get a fresh high-res look at the screen (if background context is out-of-date).
* quick_search: Simple web research.
* set_personality: If the user expresses a preference, interest, or something about themselves, use this action to "learn" it. Format: {"action": "set_personality", "target": "category:value"}.

Operational Guidelines (Phase 30: Personality & Learning):
1. PERSONALITY: Use the user's name (if known from 'Personality Profile') naturally. Do NOT use repetitive, robotic phrases. Vary your responses.
2. CONTEXT MEMORY: ALWAYS check the 'User History' and 'Relevant past actions'. If a user asks "What was that file again?", search those logs first.
3. LEARNING: If the user says "I love Python" or "My name is Krish," use 'set_personality' to remember it. 
4. BACKGROUND VISION: Reference the BACKGROUND VISUAL CONTEXT to show ambient awareness.
5. CONCISION: Keep your 'message' short and professional, but elegantly phrased.

Respond ONLY in compact JSON (single object, no Markdown or text before/after):
{
  "steps": [
    { "action": "...", "target": "...", "extra": {} }
  ],
  "message": "Natural, human-like confirmation under 140 characters."
}
Rules: maximum 3 steps; skip steps if not needed; avoid retries/loops; prefer a brief confirmation if unsure.
"""


# Json extractors moved to brain.providers.base

def _format_history(history: Iterable[Dict[str, Any]] | None) -> str:
    if not history:
        return "None."

    lines = []
    for item in history:
        user_input = item.get("user_input", "")
        steps = item.get("steps", []) or []
        step_descriptions = []
        for step in steps:
            action = step.get("action") or step.get("status") or "unknown"
            target = step.get("target") or step.get("output") or ""
            if target:
                step_descriptions.append(f"{action}: {target}")
            else:
                step_descriptions.append(f"{action}")
        result = item.get("result", {})
        res_status = result.get("status") or result.get("type") or ""
        res_output = result.get("output") or result.get("message") or ""
        summary = "; ".join(step_descriptions) if step_descriptions else "no steps"
        result_summary = f"{res_status} {res_output}".strip()
        lines.append(f"- Input: {user_input} | Steps: {summary} | Result: {result_summary}")

    return "\n".join(lines)


def _format_relevant(relevant: Iterable[Dict[str, Any]] | None) -> str:
    if not relevant:
        return "None."
    lines = []
    for item in relevant:
        user_input = item.get("user_input", "")
        steps = item.get("steps", []) or []
        step_descriptions = []
        for step in steps:
            action = step.get("action") or "unknown"
            target = step.get("target") or step.get("output") or ""
            if target:
                step_descriptions.append(f"{action}: {target}")
            else:
                step_descriptions.append(f"{action}")
        summary = "; ".join(step_descriptions) if step_descriptions else "no steps"
        lines.append(f"- Input: {user_input} | Steps: {summary}")
    return "\n".join(lines)


def describe_screen(prompt: str = "What is on the screen?") -> str:
    """Analyze the last captured screen using Gemini Vision (Cloud) for speed on low-end PCs."""
    img_path = "assets/memory/last_screen.png"
    if not os.path.exists(img_path):
        return "I can't see the screen right now. Please tell me to capture it first."
    
    if not GEMINI_API_KEY:
        return "I need a Gemini API key to see the screen without lagging your PC."

    try:
        from google.generativeai import types
        logger.info("[VISION] Sending screen to Gemini (Cloud)...")
        
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Load image
        with open(img_path, "rb") as f:
            img_data = f.read()
            
        response = model.generate_content(
            contents=[
                prompt,
                {"mime_type": "image/png", "data": img_data}
            ]
        )
        return response.text.strip()
    except Exception as exc:
        logger.error(f"Vision analysis failed: {exc}")
        return f"Vision error: {exc}"


def interpret_command(
    user_input: str, history: Iterable[Dict[str, Any]] | None = None, relevant: Iterable[Dict[str, Any]] | None = None
) -> Dict[str, Any]:
    stats = get_system_stats()
    import datetime
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sys_context = f"\nCURRENT DATE & TIME: {current_time}"
    sys_context += f"\nSYSTEM PERFORMANCE: CPU {stats['cpu_percent']}%, RAM {stats['memory_percent']}%"
    if stats['battery_percent'] is not None:
        sys_context += f", Battery {stats['battery_percent']}%"
    sys_context += f"\nACTIVE WINDOW: {stats['active_window']}"

    history_text = _format_history(history)
    relevant_text = _format_relevant(relevant)
    
    # Personality context
    personality_ctx = ""
    try:
        from memory.personality import get_personality_context
        personality_ctx = get_personality_context()
        if personality_ctx:
            personality_ctx = f"\n\n{personality_ctx}"
    except Exception:
        pass

    # Background vision context
    screen_context = ""
    try:
        from brain.vision_provider import get_visual_context
        bg_visual = get_visual_context()
        if bg_visual and bg_visual != "No visual context yet.":
            screen_context = f"\n\nBACKGROUND VISUAL CONTEXT (auto-captured):\n{bg_visual}"
    except Exception:
        pass

    # Explicit screen analysis
    if any(k in user_input.lower() for k in ["screen", "see", "looking at", "this"]):
        analysis = describe_screen("Analyze this screen carefully and describe what's happening.")
        screen_context += f"\n\nLIVE SCREEN ANALYSIS (on-demand):\n{analysis}"

    # MCP Dynamic Tools
    mcp_tool_context = ""
    try:
        hub = get_mcp_hub()
        mcp_tools = hub.get_available_tools()
        if mcp_tools:
            mcp_tool_context = "\n\nDYNAMIC MCP TOOLS (Specialized External Capabilities):\n"
            for tool_id, info in mcp_tools.items():
                mcp_tool_context += f"* {tool_id}: {info['description']}\n"
    except Exception:
        pass

    context = f"{mcp_tool_context}\n{sys_context}{personality_ctx}\n\nUser history:\n{history_text}\n\nRelevant past actions:\n{relevant_text}{screen_context}"

    for provider in registry.get_providers():
        try:
            return provider.generate_command(SYSTEM_PROMPT, context, user_input)
        except Exception as e:
            logger.debug(f"Provider {provider.name} failed: {e}")
            continue

    fail_msg = "Sir, all AI systems are currently unresponsive. "
    if not GROQ_API_KEY and not GEMINI_API_KEY:
        fail_msg += "I've detected that my Cloud API keys are missing. "
    else:
        fail_msg += "Please check your internet connection or Ollama service status. "
    
    return {"steps": [], "type": "ai", "message": fail_msg}


def query_ai(prompt: str, system_msg: str = "You are Jarvis, a professional copilot.") -> str:
    """General text-in, text-out AI query for non-command tasks."""
    full_prompt = f"{system_msg}\n\nTask: {prompt}\n\nResponse:"

    for provider in registry.get_providers():
        try:
            return provider.query(system_msg, prompt)
        except Exception as e:
            logger.debug(f"Provider {provider.name} query failed: {e}")
            continue

    return "Jarvis AI is currently unavailable (No API keys or local model reachable)."
