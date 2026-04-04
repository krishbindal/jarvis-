from __future__ import annotations

"""AI engine using Ollama as a fallback command interpreter."""

import json
from typing import Any, Dict

import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3"

SYSTEM_PROMPT = """
You are Jarvis AI.
Convert user input into a JSON list of steps. You may refer to previous outputs in next steps.

Available actions:
* open_app
* open_url
* list_files
* create_folder
* delete_file
* move_file
* copy_file
* rename_file
* search_file
* file_info
* download_file
* download_video
* convert_to_mp3
* convert_to_pdf

Respond ONLY in JSON:
{
"steps": [
  { "action": "...", "target": "...", "extra": {} }
]
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


def interpret_command(user_input: str) -> Dict[str, Any]:
    payload = {
        "model": MODEL,
        "prompt": f"{SYSTEM_PROMPT}\nUser: {user_input}\nAssistant:",
        "stream": False,
    }
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        output = data.get("response", "") or data.get("generated_text", "")
        parsed = _safe_json_extract(output)
        validated = _validate_steps(parsed)
        return validated
    except Exception as exc:  # noqa: BLE001
        return {"steps": [], "type": "ai", "message": f"AI failed: {exc}"}
