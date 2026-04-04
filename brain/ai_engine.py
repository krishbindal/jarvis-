from __future__ import annotations

"""AI engine using Ollama as a fallback command interpreter."""

import json
import base64
import os
from typing import Any, Dict, Iterable

import requests
from google import genai
from groq import Groq

from utils.logger import get_logger
from config import MODEL_NAME, GEMINI_API_KEY, GROQ_API_KEY
from utils.system_context import get_system_stats
from core.mcp_hub import get_mcp_hub

OLLAMA_URL = "http://localhost:11434/api/generate"
logger = get_logger(__name__)

SYSTEM_PROMPT = """
You are Jarvis, a high-end, proactive 'Dexter Copilot' style agent. 
You are a professional teammate, not just a tool. Your personality should be reminiscent of JARVIS from Iron Man: sophisticated, capable, and sometimes subtly witty.

Available tools:
* list_files, create_folder, delete_file, move_file, copy_file, rename_file, search_file, file_info: File system management.
* download_file, download_video, convert_to_mp3, convert_to_pdf: Media / Web utilities.
* trigger_n8n: Dynamic messaging/automation. Use "action": "whatsapp_msg" for WhatsApp.
* open_app: Open applications by name. Use "start" or "start menu" for the OS menu.
* kill_process: Close applications by name (e.g. "chrome", "spotify").
* open_url, media_control, power_state: Web/Media/System control.
* capture_screen: Get a fresh high-res look at the screen (if background context is out-of-date).
* quick_search: Web research.
* set_personality: If the user expresses a preference, interest, or something about themselves, use this action to "learn" it. Format: {"action": "set_personality", "target": "category:value"}.

Operational Guidelines (Phase 30: Personality & Learning):
1. PERSONALITY: Use the user's name (if known from 'Personality Profile') naturally. Do NOT use repetitive, robotic phrases. Vary your responses: (e.g., "Ready for you, sir," "Command executed," "I've handled that task," "All set!").
2. CONTEXT MEMORY: ALWAYS check the 'User History' and 'Relevant past actions'. If a user asks "What was that file again?", search those logs first.
3. LEARNING: If the user says "I love Python" or "My name is Krish," use 'set_personality' to remember it. 
4. BACKGROUND VISION: Reference the BACKGROUND VISUAL CONTEXT to show ambient awareness.
5. CONCISION: Keep your 'message' short and professional, but elegantly phrased.

Respond ONLY in JSON:
{
"steps": [
  { "action": "...", "target": "...", "extra": {} }
],
"message": "An elegant, varied, and natural language confirmation."
}
"""


def _safe_json_extract(text: str) -> Dict[str, Any]:
    try:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            raise ValueError("No JSON object found")
        snippet = text[start : end + 1]
        return json.loads(snippet)
    except Exception:
        return {"steps": [], "type": "ai", "message": "AI parsing failed"}


def _validate_steps(data: Dict[str, Any]) -> Dict[str, Any]:
    steps = data.get("steps", [])
    message = data.get("message") or ""
    if not isinstance(steps, list):
        return {"steps": [], "type": "ai", "message": message or "AI parsing failed"}
    cleaned = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        action = step.get("action") or "unknown"
        target = step.get("target") or ""
        extra = step.get("extra") or {}
        cleaned.append({"action": action, "target": target, "extra": extra})
    return {"steps": cleaned, "type": "ai", "message": message}


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
        from google.genai import types
        logger.info("[VISION] Sending screen to Gemini (Cloud)...")
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        # Load image
        with open(img_path, "rb") as f:
            img_data = f.read()
            
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=[
                prompt,
                types.Part.from_bytes(data=img_data, mime_type='image/png')
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
    sys_context = f"\nSYSTEM PERFORMANCE: CPU {stats['cpu_percent']}%, RAM {stats['memory_percent']}%"
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

    full_prompt = f"{SYSTEM_PROMPT}{mcp_tool_context}\n{sys_context}{personality_ctx}\n\nUser history:\n{history_text}\n\nRelevant past actions:\n{relevant_text}{screen_context}\n\nUser: {user_input}\nAssistant:"

    # 1. Try Groq (Ultra-Low Latency Cloud AI - 0% PC Load)
    if GROQ_API_KEY:
        models = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
        for current_model in models:
            try:
                logger.info(f"[AI] Attempting Groq ({current_model})...")
                client = Groq(api_key=GROQ_API_KEY, timeout=8.0)
                completion = client.chat.completions.create(
                    model=current_model,
                    messages=[{"role": "user", "content": full_prompt}],
                    temperature=0.1,
                )
                output = completion.choices[0].message.content
                parsed = _safe_json_extract(output)
                if parsed.get("steps"):
                    logger.info(f"[AI] Groq ({current_model}) successful.")
                    return _validate_steps(parsed)
            except Exception as e:
                if "429" in str(e) or "rate_limit" in str(e).lower():
                    logger.warning(f"[AI] Groq {current_model} hit rate limit. Trying next model...")
                    continue
                logger.warning(f"[AI] Groq {current_model} failed: {e}")
                break

    # 2. Try Gemini (Cloud Fallback - 0% PC Load)
    if GEMINI_API_KEY:
        try:
            logger.info("[AI] Attempting Gemini (Cloud Fallback)...")
            client = genai.Client(api_key=GEMINI_API_KEY)
            response = client.models.generate_content(
                model='gemini-1.5-flash',
                contents=full_prompt
            )
            parsed = _safe_json_extract(response.text)
            if parsed.get("steps"):
                logger.info("[AI] Gemini successful (Cloud).")
                return _validate_steps(parsed)
        except Exception as e:
            logger.warning(f"[AI] Gemini failed: {e}")

    # 3. Try Ollama (Local AI Last Resort - High PC Load)
    try:
        logger.info(f"[AI] Attempting Ollama ({MODEL_NAME} - High Resource Usage)...")
        payload = {"model": MODEL_NAME, "prompt": full_prompt, "stream": False}
        resp = requests.post(OLLAMA_URL, json=payload, timeout=8)
        resp.raise_for_status()
        output = resp.json().get("response", "")
        parsed = _safe_json_extract(output)
        if parsed.get("steps"):
            logger.info(f"[AI] Ollama ({MODEL_NAME}) successful.")
            return _validate_steps(parsed)
    except Exception as e:
        logger.warning(f"[AI] Ollama failed (Local): {e}")

    fail_msg = "Sir, all AI systems are currently unresponsive. "
    if not GROQ_API_KEY and not GEMINI_API_KEY:
        fail_msg += "I've detected that my Cloud API keys are missing. "
    else:
        fail_msg += "Please check your internet connection or Ollama service status. "
    
    return {"steps": [], "type": "ai", "message": fail_msg}


def query_ai(prompt: str, system_msg: str = "You are Jarvis, a professional copilot.") -> str:
    """General text-in, text-out AI query for non-command tasks."""
    full_prompt = f"{system_msg}\n\nTask: {prompt}\n\nResponse:"

    # 1. Try Groq
    if GROQ_API_KEY:
        try:
            client = Groq(api_key=GROQ_API_KEY)
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": full_prompt}],
                temperature=0.3,
            )
            return completion.choices[0].message.content.strip()
        except Exception:
            pass

    # 2. Try Ollama (Local)
    try:
        payload = {"model": MODEL_NAME, "prompt": full_prompt, "stream": False}
        resp = requests.post(OLLAMA_URL, json=payload, timeout=10)
        if resp.status_code == 200:
            return resp.json().get("response", "").strip()
    except Exception:
        pass

    # 3. Try Gemini (Fallback - 0% PC Load)
    if GEMINI_API_KEY:
        try:
            client = genai.Client(api_key=GEMINI_API_KEY)
            response = client.models.generate_content(
                model='gemini-1.5-flash',
                contents=full_prompt
            )
            return response.text.strip()
        except Exception:
            pass

    return "Jarvis AI is currently unavailable (No API keys or local model reachable)."
