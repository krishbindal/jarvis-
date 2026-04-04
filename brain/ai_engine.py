from __future__ import annotations

"""AI engine using Ollama as a fallback command interpreter."""

import base64
import json
import os
from typing import Any, Dict, Iterable

import requests
import config
from utils.logger import get_logger
from config import MODEL_NAME, REMOTE_MODEL_NAME, REMOTE_AI_TIMEOUT, AI_COMPLEXITY_THRESHOLD, REQUEST_TIMEOUT
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

def _should_use_remote(user_input: str) -> bool:
    tokens = user_input.split()
    return len(tokens) > 12 or any(marker in user_input.lower() for marker in ("research", "explain", "why", "how"))


def _call_local_model(payload: Dict[str, Any]) -> Dict[str, Any]:
    resp = requests.post(OLLAMA_URL, json=payload, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def _call_remote_model(prompt: str) -> Dict[str, Any]:
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("No remote AI key configured")

    headers = {"Content-Type": "application/json"}
    url = os.getenv("GEMINI_API_URL") or f"https://generativelanguage.googleapis.com/v1beta/models/{REMOTE_MODEL_NAME}:generateContent"
    params = {}
    if "OPENROUTER_API_KEY" in os.environ:
        headers["Authorization"] = f"Bearer {api_key}"
        url = "https://openrouter.ai/api/v1/chat/completions"
        payload = {"model": REMOTE_MODEL_NAME, "messages": [{"role": "user", "content": prompt}], "stream": False}
        resp = requests.post(url, headers=headers, json=payload, timeout=REMOTE_AI_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return {"response": content}

    headers["x-goog-api-key"] = api_key
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    resp = requests.post(url, headers=headers, params=params, json=payload, timeout=REMOTE_AI_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    candidates = data.get("candidates", [])
    if not candidates:
        return {"response": ""}
    return {"response": candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")}


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
    history_list = list(history or [])[-config.MAX_HISTORY_ENTRIES :]
    relevant_list = list(relevant or [])[-config.MAX_RELEVANT_ENTRIES :]
    stats = get_system_stats()
    sys_context = f"\nSYSTEM PERFORMANCE: CPU {stats['cpu_percent']}%, RAM {stats['memory_percent']}%"
    if stats['battery_percent'] is not None:
        sys_context += f", Battery {stats['battery_percent']}%"
    sys_context += f"\nACTIVE WINDOW: {stats['active_window']}"

    history_text = _format_history(history_list)
    relevant_text = _format_relevant(relevant_list)
    
    # If the user asks "what's on my screen" or "explain this screen", 
    # we should handle it specifically or inform the AI it can 'see'.
    screen_context = ""
    if any(k in user_input.lower() for k in ["screen", "see", "looking at", "this"]):
        analysis = describe_screen("Analyze this screen carefully and describe what's happening. If there's code, identify the language and purpose.")
        screen_context = f"\n\nCURRENT VISUAL CONTEXT (From your vision module):\n{analysis}"

    payload = {
        "model": MODEL_NAME,
        "prompt": f"{SYSTEM_PROMPT}\n{sys_context}\n\nUser history:\n{history_text}\n\nRelevant past actions:\n{relevant_text}{screen_context}\n\nUser: {user_input}\nAssistant:",
        "stream": False,
    }
    try:
        logger.info("[AI] Sending prompt to local model")
        prefer_remote = _should_use_remote(user_input) or (len(user_input.split()) / 10) >= AI_COMPLEXITY_THRESHOLD
        output_text = ""

        if prefer_remote:
            try:
                logger.info("[AI] Remote model preferred for complex query")
                remote_data = _call_remote_model(payload["prompt"])
                output_text = remote_data.get("response", "")
            except Exception as exc:  # noqa: BLE001
                logger.warning("[AI] Remote model unavailable, falling back to local: %s", exc)

        if not output_text:
            data = _call_local_model(payload)
            output_text = data.get("response", "") or data.get("generated_text", "")

        parsed = _safe_json_extract(output_text)
        validated = _validate_steps(parsed)
        return validated
    except Exception as exc:  # noqa: BLE001
        logger.error("AI interpretation failed: %s", exc)
        return {"steps": [], "type": "ai", "message": f"AI failed: {exc}"}
