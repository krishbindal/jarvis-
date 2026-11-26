"""Browser tasks with explicit context and evidence-based results.

Each Playwright task uses a fresh temporary browser session. It cannot inspect
or control a tab in the user's already-open Chrome/Edge window. Commands that
require an existing browser tab fail clearly instead of acting on about:blank.
"""
from __future__ import annotations

import re
from typing import Any, Dict
from urllib.parse import quote_plus

import webbrowser

from core.target_safety import inspect_open_target
from utils.logger import get_logger

logger = get_logger(__name__)
SKILL_NAME = "browser"
SKILL_DESCRIPTION = "Search Google, request browser URL opening, or read an explicitly supplied URL"
SKILL_PATTERNS = [
    r"(?:google|search\s+(?:for|the\s+web\s+for|google\s+for))\s+(.+)",
    r"search\s+(.+?)(?:\s+on\s+(?:google|the\s+web))?$",
    r"go\s+to\s+(https?://\S+|[\w.-]+\.[\w]{2,}(?:/\S*)?)",
    r"(?:read|summarize|scrape)\s+(?:this\s+)?(?:page|website|article)\s*(.*)",
    r"browse\s+(?:to\s+)?(.+)",
    r"open\s+(?:and\s+)?search\s+(?:for\s+)?(.+)",
]
_MAX_QUERY = 300
_MAX_TEXT = 2000


def _valid_url(text: str) -> str | None:
    if not isinstance(text, str):
        return None
    url = text.strip()
    if not url or len(url) > 2048 or any(c.isspace() for c in url):
        return None
    if "://" not in url:
        url = "https://" + url
    allowed, _, _ = inspect_open_target(url, "url")
    return url if allowed else None


def _run_browser_task(task_type: str, query: str) -> Dict[str, Any]:
    """Report only observed browser acceptance or newly fetched page content."""
    if task_type in {"scroll", "click_first", "extract"}:
        return {
            "success": False,
            "status": "existing_tab_unavailable",
            "message": (
                "This command requires an existing browser tab, but this skill "
                "does not attach to the user's active browser. No page was changed."
            ),
        }

    if task_type == "navigate":
        url = _valid_url(query)
        if not url:
            return {"success": False, "status": "invalid_url", "message": "Provide a valid http(s) URL or hostname."}
        try:
            accepted = webbrowser.open(url)
        except (OSError, ValueError) as exc:
            logger.warning("[BROWSER] Browser handoff failed (%s)", type(exc).__name__)
            accepted = False
        return {
            "success": bool(accepted),
            "status": "launch_requested" if accepted else "open_failed",
            "message": (
                f"Default browser accepted the URL {url}; page loading was not verified."
                if accepted else "The default browser did not accept the URL; navigation was not verified."
            ),
        }

    if task_type == "read":
        url = _valid_url(query)
        if not url:
            return {
                "success": False,
                "status": "url_required",
                "message": "Reading the current browser tab is unsupported. Supply the exact https:// URL.",
            }
    elif task_type == "search":
        if not isinstance(query, str) or not query.strip() or len(query) > _MAX_QUERY:
            return {"success": False, "status": "invalid_query", "message": "Search query must be 1–300 characters."}
        url = "https://www.google.com/search?q=" + quote_plus(query.strip())
    else:
        return {"success": False, "status": "unsupported", "message": "Unsupported browser task."}

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {
            "success": False,
            "status": "dependency_missing",
            "message": "Playwright is not installed. Install Chromium with: playwright install chromium",
        }

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                response = page.goto(url, wait_until="domcontentloaded", timeout=15000)
                if response is None or response.status >= 400:
                    return {
                        "success": False,
                        "status": "fetch_failed",
                        "message": "No successful HTTP response was observed; no content was verified.",
                    }
                if task_type == "read":
                    text = (page.inner_text("body") or "").strip()
                    if not text:
                        return {"success": False, "status": "empty_page", "message": "No readable page text was observed."}
                    excerpt = text[:_MAX_TEXT]
                    return {
                        "success": True,
                        "status": "page_text_observed",
                        "message": f"Retrieved {len(excerpt)} characters from {url}; accuracy not independently verified.",
                        "output": excerpt,
                        "source_url": url,
                    }

                headings = []
                for item in page.query_selector_all("h3")[:5]:
                    title = (item.inner_text() or "").strip()[:180]
                    if title:
                        headings.append(title)
                if not headings:
                    return {
                        "success": False,
                        "status": "no_observed_results",
                        "message": "The search page loaded but no result headings were observed.",
                    }
                return {
                    "success": True,
                    "status": "search_headings_observed",
                    "message": f"Observed {len(headings)} search headings; linked sources and claims were not independently checked.",
                    "output": "\n".join(headings),
                    "source_url": url,
                }
            finally:
                browser.close()
    except Exception as exc:
        logger.warning("[BROWSER] Playwright task failed (%s)", type(exc).__name__)
        return {
            "success": False,
            "status": "browser_error",
            "message": f"Browser task failed ({type(exc).__name__}); no successful completion was verified.",
        }


def execute(target: str, extra: Dict[str, Any] = None) -> Dict[str, Any]:
    """Route commands without assuming access to the currently active browser."""
    if not isinstance(target, str) or not target.strip():
        return {"success": False, "status": "invalid_request", "message": "A nonempty browser command is required."}
    value = target.strip()
    lower = value.lower()

    m = re.fullmatch(r"(?:go to|navigate to|browse to|browse)\s+(.+)", value, flags=re.IGNORECASE)
    if m:
        return _run_browser_task("navigate", m.group(1).strip())

    if lower.startswith(("scroll", "click", "open first result", "extract")):
        # No persistent Playwright connection exists for the user's active tab.
        operation = "scroll" if lower.startswith("scroll") else "click_first"
        return _run_browser_task(operation, value)

    m = re.fullmatch(
        r"(?:read|summarize|scrape)(?:\s+(?:this|the))?\s+(?:page|website|article)(?:\s+(.+))?",
        value, flags=re.IGNORECASE,
    )
    if m:
        return _run_browser_task("read", (m.group(1) or "").strip())

    m = re.fullmatch(
        r"(?:read|summarize|scrape)\s+(https?://\S+)", value, flags=re.IGNORECASE,
    )
    if m:
        return _run_browser_task("read", m.group(1).strip())

    query = value
    for prefix in (
        "open and search for ", "search google for ", "search the web for ",
        "search for ", "google ", "look up ", "find ", "search ",
    ):
        if lower.startswith(prefix):
            query = value[len(prefix):].strip()
            break
    return _run_browser_task("search", query)
