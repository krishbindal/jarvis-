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

OLLAMA_URL = "http://localhost:11434/api/generate"
logger = get_logger(__name__)

SYSTEM_PROMPT = """
You are Jarvis, a high-end, proactive 'Dexter Copilot' style agent. 
You are a professional teammate, not just a tool. Be concise, polite, and technically proficient.
You have universal access to the system and can see the screen.

Available tools:
* list_files: list files in a directory
* create_folder: create a new folder
* delete_file: delete a file safely
* move_file: move file from source to destination
* copy_file: copy file
* rename_file: rename file
* search_file: search files recursively
* file_info: get file details
* download_file: download file from URL
* download_video: download video from URL
* convert_to_mp3: convert file to mp3
* convert_to_pdf: convert file to pdf
* trigger_n8n: run external workflow
* open_app: open a system application
* open_url: open a website in the browser
* media_control: control playback (play, pause, next, prev, volume_up, volume_down, mute)
* power_state: system power actions (lock, sleep)
* capture_screen: capture the current screen to memory
* quick_search: search the web for real-time information

Operational Guidelines:
1. If the user asks about something on their screen, use 'capture_screen' first, then analyze.
2. If you need real-time data, use 'quick_search'.
3. Use media/power controls for OS automation requests.

Respond ONLY in JSON:
{
"steps": [
  { "action": "...", "target": "...", "extra": {} }
],
"message": "A brief, natural language confirmation of what you are doing."
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
    if not isinstance(steps, list):
        return {"steps": [], "type": "ai", "message": "AI parsing failed"}
    cleaned = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        action = step.get("action") or "unknown"
        target = step.get("target") or ""
        extra = step.get("extra") or {}
        cleaned.append({"action": action, "target": target, "extra": extra})
    return {"steps": cleaned, "type": "ai"}


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
    """Analyze the last captured screen using LLaVA vision model."""
    img_path = "assets/memory/last_screen.png"
    if not os.path.exists(img_path):
        return "I can't see the screen right now. Please tell me to capture it first."
    
    try:
        with open(img_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        
        payload = {
            "model": "llava:7b",
            "prompt": prompt,
            "images": [encoded_string],
            "stream": False,
        }
        
        logger.info("Sending screen to LLaVA vision model")
        resp = requests.post(OLLAMA_URL, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", "I see it, but I can't quite describe it.")
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
    
    # Phase 27: Inject personality context
    personality_ctx = ""
    try:
        from memory.personality import get_personality_context
        personality_ctx = get_personality_context()
        if personality_ctx:
            personality_ctx = f"\n\n{personality_ctx}"
    except Exception:
        pass

    # Phase 16: Always inject background vision context if available
    screen_context = ""
    try:
        from brain.vision_provider import get_visual_context
        bg_visual = get_visual_context()
        if bg_visual and bg_visual != "No visual context yet.":
            screen_context = f"\n\nBACKGROUND VISUAL CONTEXT (auto-captured):\n{bg_visual}"
    except Exception:
        pass

    # Additional on-demand screen analysis for explicit screen questions
    if any(k in user_input.lower() for k in ["screen", "see", "looking at", "this"]):
        analysis = describe_screen("Analyze this screen carefully and describe what's happening.")
        screen_context += f"\n\nLIVE SCREEN ANALYSIS (on-demand):\n{analysis}"

    full_prompt = f"{SYSTEM_PROMPT}\n{sys_context}{personality_ctx}\n\nUser history:\n{history_text}\n\nRelevant past actions:\n{relevant_text}{screen_context}\n\nUser: {user_input}\nAssistant:"


    # 1. Try Ollama (Local)
    try:
        logger.info("Attempting Ollama (Local AI)...")
        payload = {"model": MODEL_NAME, "prompt": full_prompt, "stream": False}
        resp = requests.post(OLLAMA_URL, json=payload, timeout=15)
        resp.raise_for_status()
        output = resp.json().get("response", "")
        parsed = _safe_json_extract(output)
        if parsed.get("steps"):
            return _validate_steps(parsed)
    except Exception as e:
        logger.warning(f"Ollama failed or model missing: {e}")

    # 2. Try Gemini (Cloud Fallback 1)
    if GEMINI_API_KEY:
        try:
            logger.info("Attempting Gemini (Cloud AI)...")
            genai.configure(api_key=GEMINI_API_KEY)
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(full_prompt)
            parsed = _safe_json_extract(response.text)
            if parsed.get("steps"):
                return _validate_steps(parsed)
        except Exception as e:
            logger.warning(f"Gemini fallback failed: {e}")

    # 3. Try Groq (Cloud Fallback 2)
    if GROQ_API_KEY:
        try:
            logger.info("Attempting Groq (Cloud AI)...")
            client = Groq(api_key=GROQ_API_KEY)
            completion = client.chat.completions.create(
                model="llama3-70b-8192",
                messages=[{"role": "user", "content": full_prompt}],
                temperature=0.1,
            )
            output = completion.choices[0].message.content
            parsed = _safe_json_extract(output)
            if parsed.get("steps"):
                return _validate_steps(parsed)
        except Exception as e:
            logger.warning(f"Groq fallback failed: {e}")

    return {"steps": [], "type": "ai", "message": "All AI providers failed. Please check connectivity or API keys."}
