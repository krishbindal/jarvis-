from __future__ import annotations

"""Low-latency streaming helpers for local/edge LLM responses."""

import json
import logging
from typing import Generator, Iterable, List, Optional

import requests
from groq import Groq

from config import MODEL_NAME, GROQ_API_KEY
from utils.logger import get_logger

logger = get_logger(__name__)

OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"


def _stream_ollama(messages: List[dict]) -> Generator[str, None, None]:
    """Yield tokens from a local Ollama chat stream."""
    try:
        resp = requests.post(
            OLLAMA_CHAT_URL,
            json={"model": MODEL_NAME, "messages": messages, "stream": True},
            stream=True,
            timeout=10,
        )
        resp.raise_for_status()

        for raw in resp.iter_lines():
            if not raw:
                continue
            try:
                data = json.loads(raw.decode("utf-8"))
            except Exception:
                continue
            token = data.get("message", {}).get("content") or data.get("response")
            if token:
                yield token
            if data.get("done"):
                break
    except Exception as exc:  # noqa: BLE001
        logger.warning("[STREAM] Ollama stream failed: %s", exc)


def _stream_groq(messages: List[dict]) -> Generator[str, None, None]:
    """Yield tokens from Groq streaming as a fallback."""
    if not GROQ_API_KEY:
        return
    try:
        client = Groq(api_key=GROQ_API_KEY, timeout=10.0)
        stream = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            temperature=0.2,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta
            token = delta.content or ""
            if token:
                yield token
    except Exception as exc:  # noqa: BLE001
        logger.warning("[STREAM] Groq stream failed: %s", exc)


def stream_response(user_prompt: str, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
    """
    Stream a short response with preference for local Ollama, then Groq.

    This is intentionally lightweight to keep perceived latency low while
    narrating progress back to the UI and TTS layers.
    """
    messages: List[dict] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})

    # Try local first
    for token in _stream_ollama(messages):
        yield token

    # If nothing was yielded, fall back to Groq
    if GROQ_API_KEY:
        for token in _stream_groq(messages):
            yield token
