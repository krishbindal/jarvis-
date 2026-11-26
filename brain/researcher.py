"""Source-backed, limited encyclopedia lookup for Jarvis.

This is NOT comprehensive deep research or a live web-wide search engine.
It retrieves real Wikipedia excerpts and exposes their actual source links.
It never fabricates references or asks an LLM to pretend it accessed pages.
"""
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import requests

from utils.logger import get_logger

logger = get_logger(__name__)
_API = "https://en.wikipedia.org/w/api.php"
_MAX_RESULTS = 5
_TIMEOUT = (3, 12)


def _article_sources(topic: str, limit: int) -> list[dict[str, str]]:
    """Fetch real article intros; reject untrusted/broken source URLs."""
    response = requests.get(
        _API,
        params={
            "action": "query",
            "generator": "search",
            "gsrsearch": topic,
            "gsrlimit": limit,
            "prop": "extracts|info",
            "exintro": "1",
            "explaintext": "1",
            "exchars": 800,
            "inprop": "url",
            "format": "json",
            "formatversion": "2",
        },
        headers={"User-Agent": "JarvisX-Desktop/1.0 (source-grounded personal research tool)"},
        timeout=_TIMEOUT,
        allow_redirects=False,
    )
    response.raise_for_status()
    # A redirect or HTTP error cannot be silently treated as sourced research.
    if response.status_code != 200:
        raise ValueError("Research API did not return a valid response")
    data: Any = response.json()
    if not isinstance(data, dict):
        return []
    pages = data.get("query", {})
    if not isinstance(pages, dict) or not isinstance(pages.get("pages"), list):
        return []

    results = []
    for page in pages["pages"][:limit]:
        if not isinstance(page, dict):
            continue
        title = page.get("title")
        url = page.get("fullurl")
        excerpt = page.get("extract")
        if not all(isinstance(item, str) for item in (title, url, excerpt)):
            continue
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.netloc != "en.wikipedia.org" or not parsed.path.startswith("/wiki/"):
            continue
        excerpt = " ".join(excerpt.split())[:800]
        if not title.strip() or not excerpt:
            continue
        results.append({
            "title": title.strip()[:200],
            "url": url,
            "excerpt": excerpt,
        })
    return results


class DeepResearchAgent:
    """Retrieves attributable excerpts, avoiding unsupported AI synthesis."""

    def __init__(self, event_bus):
        self._events = event_bus
        self.source_count = 0

    def perform_research(self, topic: str, max_steps: int = 3) -> str:
        """Return source-linked excerpts, not invented research findings."""
        self.source_count = 0
        topic = topic.strip() if isinstance(topic, str) else ""
        if not topic or len(topic) > 300:
            return "No verified research performed. Provide a topic of 1–300 characters."

        try:
            limit = max(1, min(_MAX_RESULTS, int(max_steps)))
        except (TypeError, ValueError):
            limit = 3
        try:
            sources = _article_sources(topic, limit)
        except (requests.RequestException, ValueError, TypeError) as exc:
            logger.warning("[RESEARCH] Source retrieval unavailable (%s)", type(exc).__name__)
            return (
                "Source retrieval failed. No references were verified, "
                "so Jarvis cannot claim to have researched this topic."
            )

        if not sources:
            return (
                "No attributable encyclopedia excerpts were retrieved. "
                "Jarvis cannot claim that research was completed."
            )

        self.source_count = len(sources)
        lines = [
            f"Limited sourced overview: {topic}",
            "",
            f"Retrieved {self.source_count} Wikipedia article excerpts. "
            "This is NOT a comprehensive web search or independent fact-check.",
            "",
        ]
        for index, source in enumerate(sources, start=1):
            lines.extend([
                f"[{index}] {source['title']}",
                f"Source: {source['url']}",
                f"Excerpt: {source['excerpt']}",
                "",
            ])
        return "\n".join(lines)
