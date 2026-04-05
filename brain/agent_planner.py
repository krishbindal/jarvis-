from __future__ import annotations

"""LLM-driven planner that proposes next tool calls based on context."""

import json
import re
from typing import Any, Dict, List, Tuple

import requests
from groq import Groq

from config import MODEL_NAME, GROQ_API_KEY
from utils.logger import get_logger

logger = get_logger(__name__)

OLLAMA_URL = "http://localhost:11434/api/generate"

SYSTEM_PROMPT = """
You are Jarvis, an autonomous agent. Plan the NEXT action(s) only — no hardcoded app/site flows.
Strict reply format:
ACTION: <tool>("input") # optional short reason
...multiple ACTION lines allowed (max 3)...
FINAL: <concise status/message>
OR reply as JSON: {"steps":[{"tool":"...", "input":"...", "reason":"..."}], "message":"..."}.
Available tools:
- open_app(name): focus or launch an app.
- type_text(text): type text at the focused field.
- press_key(key): press a key or combo (Ctrl+L for address bar, Enter to submit).
- click(description): simple click at current cursor location.
- read_screen(): capture screen and return path + active app hints.
- get_active_app(): returns active window/process.
- open_url(url): open or reuse a browser with a URL.
Guidelines:
- Use current_app/current_url to continue in the same surface; avoid app/site-specific if/else.
- Keep to the next 1-3 minimal steps; prefer single-step increments when uncertain.
- If task seems complete, return empty steps with a brief confirmation.
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


_ACTION_RE = re.compile(
    r"^\s*action\s*:\s*(?P<tool>[a-zA-Z_]+)(?:\s*\(\s*(?P<input>[^)]*)\s*\))?",
    re.IGNORECASE,
)


def _extract_actions(text: str) -> Tuple[List[Dict[str, Any]], str]:
    steps: List[Dict[str, Any]] = []
    message = ""
    for line in text.splitlines():
        cleaned_line = line.strip()
        m = _ACTION_RE.search(cleaned_line)
        if not m:
            continue
        tool = (m.group("tool") or "").strip()
        raw_input = (m.group("input") or "").strip()
        cleaned_input = raw_input.strip(' "\'')
        reason = ""
        if "#" in cleaned_line:
            reason = cleaned_line.split("#", 1)[1].strip()
        if tool:
            steps.append({"tool": tool, "input": cleaned_input, "reason": reason})
    for line in reversed(text.splitlines()):
        if line.lower().startswith(("final:", "message:", "status:")):
            message = line.split(":", 1)[1].strip()
            break
    return steps, message


def plan_steps(command: str, context: Dict[str, Any], screen_context: str = "", feedback: str = "") -> Tuple[List[Dict[str, Any]], str]:
    prompt = f"""User command: {command}
Context (persistent across turns): {json.dumps(context)}
Recent result/feedback: {feedback or "None"}
Screen: {screen_context or "None"}

Rules:
- Pick the next 1-3 minimal tool calls to advance the task.
- Reuse current_app/current_url when present instead of re-opening surfaces.
- When uncertain, call get_active_app or read_screen before acting.
- No site/app-specific logic; rely only on the tools and context.
- Respond ONLY with the strict format: ACTION: <tool>(\"input\") #reason and a FINAL line, or the JSON equivalent."""

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

    if not steps:
        steps, extracted_msg = _extract_actions(raw)
        message = message or extracted_msg

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
