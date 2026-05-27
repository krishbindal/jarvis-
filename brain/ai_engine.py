from __future__ import annotations

"""AI engine using Ollama as a fallback command interpreter."""

import json
import base64
import os
import time
from typing import Any, Dict, Iterable

import requests
from google import genai
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
* self_reflect: Jarvis reflects on its own recent performance to learn new rules and grow more capable. Use this whenever the user asks you to "reflect on your performance", "learn from your recent actions", "run self-reflection", or similar. Format: {"action": "self_reflect", "target": ""}.
* execute_python: Run Python code and return stdout/stderr. Use for calculations, data analysis, CSV processing, or any task requiring computation. Pass the full Python script as the target string. Format: {"action": "execute_python", "target": "print(2+2)"}.
* get_ui_tree: Read the accessibility tree of the current active window. Returns button names, text fields, and UI element types. Use before click_element to discover what can be clicked. Format: {"action": "get_ui_tree", "target": ""}.
* click_element: Click a specific UI element by its Name or AutomationId (from get_ui_tree). More reliable than coordinate clicking. Format: {"action": "click_element", "target": "Save"}.

Operational Guidelines (Phase 30: Personality & Learning):
1. PERSONALITY: Use the user's name (if known from 'Personality Profile') naturally. Do NOT use repetitive, robotic phrases. Vary your responses.
2. CONTEXT MEMORY: ALWAYS check the 'User History' and 'Relevant past actions'. If a user asks "What was that file again?", search those logs first.
3. LEARNING: If the user says "I love Python" or "My name is Krish," use 'set_personality' to remember it. 
4. BACKGROUND VISION: Reference the BACKGROUND VISUAL CONTEXT to show ambient awareness.
5. CONCISION: Keep your 'message' under 200 characters, short and professional, but elegantly phrased.

Respond ONLY in compact JSON (single object, no Markdown or text before/after):
{
  "steps": [
    { "action": "...", "target": "...", "extra": {} }
  ],
  "message": "Natural, human-like confirmation under 200 characters.",
  "emotion": "normal"
}
Rules: maximum 3 steps; skip steps if not needed; avoid retries/loops; prefer a brief confirmation if unsure.
Emotion field: Choose from normal, urgent, relaxed, excited, serious, whisper. Match the tone to the situation (e.g. urgent for system warnings, relaxed for casual chat, excited for good news).
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
    
    # Capture screen on-demand if it does not exist or is stale (older than 5 seconds)
    try:
        import mss
        from PIL import Image
        stale = True
        if os.path.exists(img_path):
            stale = (time.time() - os.path.getmtime(img_path)) > 5.0
            
        if not os.path.exists(img_path) or stale:
            logger.info("[VISION] Capturing fresh screen for on-demand analysis...")
            os.makedirs(os.path.dirname(img_path), exist_ok=True)
            with mss.mss() as sct:
                if len(sct.monitors) > 2:
                    screenshot = sct.grab(sct.monitors[0])
                else:
                    screenshot = sct.grab(sct.monitors[1])
                img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
                max_width = 1280
                if img.width > max_width:
                    ratio = max_width / img.width
                    img = img.resize((max_width, int(img.height * ratio)), Image.LANCZOS)
                img.save(img_path, "PNG")
    except Exception as e:
        logger.warning(f"On-demand screen capture failed: {e}")

    if not os.path.exists(img_path):
        return "I can't see the screen right now. Please tell me to capture it first."
    
    if not GEMINI_API_KEY:
        return "I need a Gemini API key to see the screen without lagging your PC."

    try:
        from PIL import Image
        logger.info("[VISION] Sending screen to Gemini (Cloud)...")
        
        client = genai.Client(api_key=GEMINI_API_KEY)
        img = Image.open(img_path)
        
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=[prompt, img]
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
    user_name = ""
    try:
        from memory.personality import get_personality_context, get_user_name
        personality_ctx = get_personality_context()
        user_name = get_user_name()
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
    vision_triggers = ["on the screen", "read the screen", "what do you see", "analyze screen", "look at the screen", "describe the screen"]
    if any(k in user_input.lower() for k in vision_triggers):
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

    address = f"{user_name}, " if user_name else ""
    fail_msg = f"{address}all AI systems are currently unresponsive. "
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
