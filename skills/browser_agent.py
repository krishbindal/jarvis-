"""
JARVIS-X Phase 21: Browser Autopilot

Skill: Automate browser tasks via Playwright.
Handles: "search google for X", "go to URL", "read this page"
"""

import threading
from typing import Any, Dict
from utils.logger import get_logger

logger = get_logger(__name__)

SKILL_NAME = "browser"
SKILL_DESCRIPTION = "Browser automation — 'search for React guides', 'go to github.com', 'read this page'"
SKILL_PATTERNS = [
    r"(?:google|search\s+(?:for|the\s+web\s+for|google\s+for))\s+(.+)",
    r"search\s+(.+?)(?:\s+on\s+(?:google|the\s+web))?$",
    r"go\s+to\s+(https?://\S+|[\w.-]+\.[\w]{2,}(?:/\S*)?)",
    r"(?:read|summarize|scrape)\s+(?:this\s+)?(?:page|website|article)\s*(.*)",
    r"browse\s+(?:to\s+)?(.+)",
    r"open\s+(?:and\s+)?search\s+(?:for\s+)?(.+)",
]


def _run_browser_task(task_type: str, query: str) -> Dict[str, Any]:
    """Execute browser automation in a sync context."""
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()

            if task_type == "search":
                url = f"https://www.google.com/search?q={query}"
                page.goto(url, wait_until="domcontentloaded", timeout=15000)

                # Extract top results
                results = []
                items = page.query_selector_all("h3")
                for item in items[:5]:
                    text = item.inner_text()
                    if text:
                        results.append(text)

                summary = "\n".join(f"• {r}" for r in results) if results else "No results found."

                # Keep browser open for user
                logger.info("[BROWSER] Search results: %s", summary[:200])
                return {
                    "success": True,
                    "status": "success",
                    "message": f"Here are the top results for '{query}':\n{summary}",
                    "output": summary,
                }

            elif task_type == "navigate":
                if not query.startswith("http"):
                    query = f"https://{query}"
                page.goto(query, wait_until="domcontentloaded", timeout=15000)
                title = page.title()

                return {
                    "success": True,
                    "status": "success",
                    "message": f"Navigated to: {title}",
                    "output": title,
                }

            elif task_type == "read":
                # Get page text content
                text = page.inner_text("body")
                # Truncate to reasonable length
                text = text[:2000] if text else "Could not read page content."

                return {
                    "success": True,
                    "status": "success",
                    "message": f"Page content (first 2000 chars):\n{text[:500]}...",
                    "output": text,
                }
            
            elif task_type == "scroll":
                logger.execution("Scrolling browser...")
                page.mouse.wheel(0, 800)
                import time
                time.sleep(2)
                return {"success": True, "message": "Sir, I have scrolled down the page."}

            elif task_type == "click_first":
                logger.execution("Clicking first result...")
                # Modern Google results often use h3 or specific anchor tags
                selector = "h3 >> nth=0"
                if page.query_selector(selector):
                    page.click(selector)
                    return {"success": True, "message": "Sir, I have opened the first result."}
                return {"success": False, "message": "Could not find a clickable result."}

            elif task_type == "extract":
                logger.execution(f"Extracting data for: {query}")
                # For weather/temp, LLM-based selector search or hardcoded common ones
                if "weather" in query or "temperature" in query:
                    temp = page.query_selector("#wob_tm") # Google specialized weather widget
                    if temp:
                        val = temp.inner_text()
                        return {"success": True, "message": f"The current temperature is {val}°C, Sir."}
                
                # Generic fallback: just return truncated text
                text = page.inner_text("body")[:500]
                return {"success": True, "message": f"Extracted: {text}"}

    except ImportError:
        return {
            "success": False,
            "status": "error",
            "message": "Playwright not installed. Run: playwright install chromium",
        }
    except Exception as e:
        logger.error("[BROWSER] Task failed: %s", e)
        return {"success": False, "status": "error", "message": f"Browser error: {e}"}


def execute(target: str, extra: Dict[str, Any] = None) -> Dict[str, Any]:
    """Route browser commands."""
    import re
    target_lower = target.lower().strip()

    target_lower = target.lower().strip()
    logger.action(f"Browser Task: {target_lower}")

    # Advanced Multi-Step Handlers
    if "open" in target_lower and "result" in target_lower:
        return _run_browser_task("click_first", "")
    
    if "scroll" in target_lower:
        return _run_browser_task("scroll", target_lower)

    if "extract" in target_lower or "weather" in target_lower:
        return _run_browser_task("extract", target_lower)

    # Detect task type
    if any(w in target_lower for w in ["search", "google", "look up", "find"]):
        # Extract search query
        query = target_lower
        for prefix in ["search for ", "google ", "search google for ", "search the web for ",
                       "look up ", "find ", "search ", "open and search for "]:
            if query.startswith(prefix):
                query = query[len(prefix):]
                break
        return _run_browser_task("search", query.strip())

    elif any(w in target_lower for w in ["go to", "navigate", "browse to"]):
        url = target_lower
        for prefix in ["go to ", "navigate to ", "browse to ", "browse "]:
            if url.startswith(prefix):
                url = url[len(prefix):]
                break
        return _run_browser_task("navigate", url.strip())

    elif any(w in target_lower for w in ["read", "summarize", "scrape"]):
        return _run_browser_task("read", target_lower)

    # Default: treat as search
    return _run_browser_task("search", target_lower)
