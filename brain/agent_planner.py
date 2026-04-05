from __future__ import annotations

"""LLM-driven planner that proposes next tool calls based on context."""

import json
from typing import Any, Dict, List, Tuple

import requests
from groq import Groq

from config import MODEL_NAME, GROQ_API_KEY
from utils.logger import get_logger

logger = get_logger(__name__)

OLLAMA_URL = "http://localhost:11434/api/generate"

SYSTEM_PROMPT = """
You are Jarvis, an autonomous agent. Decide the next minimal tool actions to fulfill the user's intent.
Always return a JSON object: {"steps":[{"tool":"...", "input":"...", "reason":"..."}], "message":"..."}.
Available tools:
- open_app(name): focus or launch an app.
- type_text(text): type text at the focused field.
- press_key(key): press a key or combo (use Ctrl+L to focus address bar, Enter to submit).
- click(description): simple click at current cursor location.
- read_screen(): capture screen and return path plus active app hints.
- get_active_app(): returns active window/process.
Guidelines:
- Prefer short, decisive steps.
- Use current_app/current_url to continue inside the same surface (no hardcoded site logic).
- If task seems done, return an empty steps list and a brief message.
"""


def _call_ollama(prompt: str) -> str:
    resp = requests.post(OLLAMA_URL, json={"model": MODEL_NAME, "prompt": prompt, "stream": False}, timeout=8)
    resp.raise_for_status()
    return resp.json().get("response", "")


def _call_groq(prompt: str) -> str:
    if not GROQ_API_KEY:
        raise RuntimeError("No Groq key")
    client = Groq(api_key=GROQ_API_KEY, timeout=8.0)
    completion = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
        temperature=0.2,
    )
    return completion.choices[0].message.content or ""


def _extract_json(text: str) -> Dict[str, Any]:
    try:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            return {}
        return json.loads(text[start : end + 1])
    except Exception:
        return {}


def plan_steps(command: str, context: Dict[str, Any], screen_context: str = "") -> Tuple[List[Dict[str, Any]], str]:
    prompt = f"""User command: {command}
Context: {json.dumps(context)}
Screen: {screen_context or "None"}
Respond with JSON as specified."""

    raw = ""
    try:
        raw = _call_groq(prompt)
    except Exception as exc:
        logger.debug("[AGENT] Groq planner failed: %s", exc)
    if not raw:
        try:
            raw = _call_ollama(f"{SYSTEM_PROMPT}\n{prompt}")
        except Exception as exc:  # noqa: BLE001
            logger.error("[AGENT] Planner failed: %s", exc)
            return [], "Planner unavailable."

    parsed = _extract_json(raw)
    steps = parsed.get("steps") or []
    message = parsed.get("message") or ""
    cleaned = []
    for step in steps:
        tool = step.get("tool")
        if not tool:
            continue
        cleaned.append({
            "tool": tool,
            "input": step.get("input", ""),
            "reason": step.get("reason", ""),
        })
    return cleaned, message
