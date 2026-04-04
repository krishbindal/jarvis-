from __future__ import annotations

"""AI engine using Ollama as a fallback command interpreter."""

import json
from typing import Any, Dict, Iterable

import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3"

SYSTEM_PROMPT = """
You are Jarvis AI.
Convert user input into a JSON list of steps. You may refer to previous outputs in next steps. Relevant past actions may be provided to help you plan.

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
* trigger_n8n

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


def interpret_command(
    user_input: str, history: Iterable[Dict[str, Any]] | None = None, relevant: Iterable[Dict[str, Any]] | None = None
) -> Dict[str, Any]:
    history_text = _format_history(history)
    relevant_text = _format_relevant(relevant)
    payload = {
        "model": MODEL,
        "prompt": f"{SYSTEM_PROMPT}\nUser history:\n{history_text}\n\nRelevant past actions:\n{relevant_text}\n\nUser: {user_input}\nAssistant:",
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
