from __future__ import annotations

"""LLM-driven planner that proposes next tool calls based on context."""

import json
import re
from typing import Any, Dict, List, Tuple

import requests
from groq import Groq

from config import MODEL_NAME, GROQ_API_KEY
from brain.structured_output import (
    MAX_STEPS,
    clean_message,
    normalize_tool_steps,
    parse_structured_response,
)
from utils.logger import get_logger

logger = get_logger(__name__)

OLLAMA_URL = "http://localhost:11434/api/generate"

ALLOWED_TOOLS = {
    "open_app",
    "type_text",
    "press_key",
    "click",
    "read_screen",
    "get_active_app",
    "open_url",
    "scroll",
}

STRICT_FORMAT = """
Return ONLY JSON in one line (no Markdown, no prose):
{"action":"plan","say":"short, human-like status","steps":[{"tool":"open_app","input":"...", "reason":""}]}
Rules:
- steps: max 3, each tool in [open_app, type_text, press_key, click, read_screen, get_active_app, open_url, scroll]
- keep input concise; omit if not needed.
- 'say' must be a single friendly sentence (<=140 chars) fit for speech/UI.
- no extra keys, no explanations before/after the JSON.
"""

SYSTEM_PROMPT = f"""
You are Jarvis, an autonomous agent. Plan the NEXT action(s) only — no hardcoded app/site flows.
{STRICT_FORMAT}
Available tools:
- open_app(name): focus or launch an app.
- type_text(text): type text at the focused field.
- press_key(key): press a key or combo (Ctrl+L for address bar, Enter to submit).
- click(description): simple click at current cursor location.
- read_screen(): capture screen and return path + active app hints.
- get_active_app(): returns active window/process.
- open_url(url): open or reuse a browser with a URL.
- scroll(amount): scroll vertically by pixels (negative = down).
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


_ACTION_RE = re.compile(r"^\s*action\s*:\s*(?P<tool>[a-zA-Z_]+)(?:\s*\(\s*(?P<input>[^)]*)\s*\))?", re.IGNORECASE)


def _extract_actions(text: str) -> Tuple[List[Dict[str, Any]], str]:
    steps: List[Dict[str, Any]] = []
    message = ""
    seen = set()
    for line in text.splitlines():
        cleaned_line = line.strip()
        m = _ACTION_RE.search(cleaned_line)
        if not m:
            continue
        tool = (m.group("tool") or "").strip()
        if tool and tool not in ALLOWED_TOOLS:
            continue
        raw_input = (m.group("input") or "").strip()
        cleaned_input = raw_input.strip(' "\'')
        reason = ""
        if "#" in cleaned_line:
            reason = cleaned_line.split("#", 1)[1].strip()
        key = (tool, cleaned_input, reason)
        if tool and key not in seen:
            seen.add(key)
            steps.append({"tool": tool, "input": cleaned_input, "reason": reason})
        if len(steps) >= MAX_STEPS:
            break
    for line in reversed(text.splitlines()):
        if line.lower().startswith(("final:", "message:", "status:")):
            message = line.split(":", 1)[1].strip()
            break
    return steps, message


def plan_steps(command: str, context: Dict[str, Any], screen_context: str = "", feedback: str = "") -> Tuple[List[Dict[str, Any]], str]:
    if not command:
        return [], "No command provided."

    prompt = f"""User command: {command}
Context (persistent across turns): {json.dumps(context)}
Recent result/feedback: {feedback or "None"}
Screen: {screen_context or "None"}

Rules:
- Pick the next 1-3 minimal tool calls to advance the task.
- Reuse current_app/current_url when present instead of re-opening surfaces.
- When uncertain, call get_active_app or read_screen before acting.
- No site/app-specific logic; rely only on the tools and context.
- Respond ONLY with the strict JSON format shown above."""

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

    steps, message = parse_structured_response(raw, ALLOWED_TOOLS, default_message="Ready.", max_steps=MAX_STEPS)

    if not steps:
        action_lines, extracted_msg = _extract_actions(raw)
        steps = normalize_tool_steps(action_lines, ALLOWED_TOOLS, max_steps=MAX_STEPS)
        message = message or extracted_msg

    message = clean_message(message, default="Ready.")
    return steps, message
