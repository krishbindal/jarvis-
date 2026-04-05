from __future__ import annotations

"""
Universal Dynamic Command Router for JARVIS-X Dexter Copilot.

Architecture (Phase 14 — Clean Separation):
    command_parser.py  → NLP normalization, multi-step split, session context
    command_cache.py   → LRU cache for repeated commands
    command_router.py  → Pattern matching + dynamic type detection (this file)
    action_registry.py → Execution engine with self-healing fallback

All natural language → NO hardcoded sites/apps → dynamic type detection.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional

from utils.logger import get_logger
from core.command_spec import COMMAND_SPEC
from core.network_spec import NETWORK_SPEC
from core.command_parser import normalize, split_multi_step, session
from core.command_cache import route_cache
from skills import match_skill

logger = get_logger(__name__)

# ─────────────────────────────────────────────────
# Extensible Lookup Tables (not hardcoded logic)
# ─────────────────────────────────────────────────

_SITE_SHORTCUTS = {
    "youtube":   "https://www.youtube.com",
    "google":    "https://www.google.com",
    "github":    "https://www.github.com",
    "gmail":     "https://mail.google.com",
    "reddit":    "https://www.reddit.com",
    "twitter":   "https://www.twitter.com",
    "x":         "https://www.x.com",
    "instagram": "https://www.instagram.com",
    "facebook":  "https://www.facebook.com",
    "linkedin":  "https://www.linkedin.com",
    "whatsapp":  "https://web.whatsapp.com",
    "spotify":   "https://open.spotify.com",
    "netflix":   "https://www.netflix.com",
    "amazon":    "https://www.amazon.com",
    "chatgpt":   "https://chat.openai.com",
    "stackoverflow": "https://stackoverflow.com",
    "wikipedia": "https://www.wikipedia.org",
    "twitch":    "https://www.twitch.tv",
}

_FOLDER_MAP = {
    "downloads": str(Path("~").expanduser() / "Downloads"),
    "desktop":   str(Path("~").expanduser() / "Desktop"),
    "documents": str(Path("~").expanduser() / "Documents"),
    "pictures":  str(Path("~").expanduser() / "Pictures"),
    "music":     str(Path("~").expanduser() / "Music"),
    "videos":    str(Path("~").expanduser() / "Videos"),
    "home":      str(Path("~").expanduser()),
}

_FILE_EXTS = (
    ".pdf", ".txt", ".docx", ".xlsx", ".pptx", ".csv",
    ".py", ".js", ".ts", ".html", ".css", ".json", ".md", ".xml", ".yaml", ".yml",
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg",
    ".mp4", ".mp3", ".wav", ".avi", ".mkv", ".mov",
    ".zip", ".rar", ".7z", ".tar", ".gz",
    ".exe", ".bat", ".msi", ".sh",
    ".log", ".ini", ".cfg", ".conf", ".env",
)

_APP_MAP = {
    "chrome":   "chrome",
    "edge":     "msedge",
    "firefox":  "firefox",
    "brave":    "brave",
    "opera":    "opera",
    "vscode":   "code",
    "vs code":  "code",
    "visual studio code": "code",
    "notepad":  "notepad",
    "notepad++": "notepad++",
    "explorer": "explorer",
    "file explorer": "explorer",
    "cmd":      "cmd",
    "terminal": "wt",
    "powershell": "powershell",
    "word":     "winword",
    "excel":    "excel",
    "powerpoint": "powerpnt",
    "discord":  "discord",
    "spotify":  "spotify",
    "steam":    "steam",
    "vlc":      "vlc",
    "obs":      "obs64",
    "task manager": "taskmgr",
    "calculator": "calc",
    "settings": "ms-settings:",
    "paint":    "mspaint",
}

_MEDIA_KEYWORDS = {
    "play": "play", "pause": "pause", "stop": "stop",
    "next": "next", "previous": "previous", "skip": "next",
    "volume up": "volume_up", "turn up": "volume_up", "louder": "volume_up",
    "volume down": "volume_down", "turn down": "volume_down", "quieter": "volume_down",
    "mute": "mute", "unmute": "mute", "resume": "play",
}

_GREETINGS = (
    "hi", "hello", "hey", "what's up", "whats up", "sup",
    "good morning", "good evening", "good afternoon",
    "how are you", "how r u", "how are u", "you there",
    "are you there", "wake up", "thanks", "thank you",
    "bye", "goodbye", "see you", "good night",
    "yo", "hola",
)

_PLACEHOLDER_FIELDS = ("path", "name", "src", "dest", "new_name", "root_path")


# ─────────────────────────────────────────────────
# Target Intelligence (Phase 2)
# ─────────────────────────────────────────────────

def _classify_target(target: str) -> str:
    t = target.lower().strip()
    if t.startswith("http://") or t.startswith("https://"):
        return "url"
    if any(ext in t for ext in (".com", ".org", ".net", ".io", ".dev", ".co", ".tv", ".me")):
        return "url"
    if t in _SITE_SHORTCUTS:
        return "url"
    if any(t.endswith(ext) for ext in _FILE_EXTS):
        return "file"
    if t in _FOLDER_MAP or any(kw in t for kw in ("folder", "directory", "dir")):
        return "folder"
    return "unknown"


def _resolve_url(target: str) -> str:
    t = target.lower().strip()
    if t.startswith("http://") or t.startswith("https://"):
        return t
    if t in _SITE_SHORTCUTS:
        return _SITE_SHORTCUTS[t]
    
    # Improved YouTube Search Pattern
    yt_search = re.match(r"(?:youtube|play)\s*(?:on\s+youtube|for|of)?\s*(.+)$", t)
    if "youtube" in t and yt_search:
        query = yt_search.group(1).strip().replace(" ", "+")
        return f"https://www.youtube.com/results?search_query={query}"

    if any(ext in t for ext in (".com", ".org", ".net", ".io", ".dev", ".co", ".tv", ".me")):
        return f"https://{t}" if not t.startswith("www.") else f"https://{t}"
    return f"https://www.google.com/search?q={target.replace(' ', '+')}"


def _resolve_folder(target: str) -> str:
    t = target.lower().strip()
    t = re.sub(r"\s*(folder|directory|dir)$", "", t).strip()
    return _FOLDER_MAP.get(t, target)


def _resolve_app(app_name: str) -> str:
    return _APP_MAP.get(app_name.lower().strip(), app_name.lower().strip())


# ─────────────────────────────────────────────────
# Build helpers
# ─────────────────────────────────────────────────

def _build(action: str, target: str, message: str, extra: Optional[dict] = None) -> Dict:
    result = {"action": action, "target": target, "message": message, "type": "system"}
    if extra:
        result["extra"] = extra
    return result


def _clean(val: str) -> str:
    return val.strip().strip('"').strip("'")


# ─────────────────────────────────────────────────
# Spec matchers (file/network commands from JSON)
# ─────────────────────────────────────────────────

def _phrase_to_regex(phrase: str) -> re.Pattern[str]:
    pattern = re.escape(phrase.lower())
    for field in _PLACEHOLDER_FIELDS:
        pattern = pattern.replace(r"\{" + field + r"\}", rf"(?P<{field}>.+)")
    pattern = pattern.replace(r"\ ", r"\s+")
    return re.compile(rf"{pattern}", re.IGNORECASE)


def _build_file_command(action: str, groups: Dict[str, str]) -> Dict[str, str]:
    cleaned = {k: _clean(v) for k, v in groups.items()}
    extra_map = {
        "list_files":    lambda c: {"target": c.get("path", ""), "extra": {}},
        "create_folder": lambda c: {"target": c.get("name", ""), "extra": {"path": c.get("path", "")}},
        "delete_file":   lambda c: {"target": c.get("path", ""), "extra": {}},
        "move_file":     lambda c: {"target": c.get("dest", ""), "extra": {"source": c.get("src", "")}},
        "copy_file":     lambda c: {"target": c.get("dest", ""), "extra": {"source": c.get("src", "")}},
        "rename_file":   lambda c: {"target": c.get("path", ""), "extra": {"new_name": c.get("new_name", "")}},
        "search_file":   lambda c: {"target": c.get("name", ""), "extra": {"root_path": c.get("root_path", "")}},
        "file_info":     lambda c: {"target": c.get("path", ""), "extra": {}},
    }
    mapper = extra_map.get(action)
    if mapper:
        result = mapper(cleaned)
        return {"action": action, "target": result["target"], "extra": result["extra"],
                "type": "file", "message": action.replace("_", " ").title()}
    return {"action": "unknown", "target": "", "extra": {}, "type": "file", "message": "Unknown file command"}


def _match_file_command(normalized: str) -> Dict | None:
    for spec in COMMAND_SPEC:
        action = spec.get("action", "")
        for phrase in spec.get("phrases", []):
            m = _phrase_to_regex(phrase).match(normalized)
            if m:
                return _build_file_command(action, m.groupdict())
    return None


def _match_network_command(normalized: str) -> Dict | None:
    for spec in NETWORK_SPEC:
        action = spec.get("action", "")
        cmd_type = spec.get("type", "network")
        for phrase in spec.get("phrases", []):
            m = _phrase_to_regex(phrase).match(normalized)
            if m:
                cleaned = {k: _clean(v) for k, v in m.groupdict().items()}
                target = cleaned.get("url") or cleaned.get("path") or ""
                return {"action": action, "target": target, "extra": cleaned,
                        "type": cmd_type, "message": "Processing network request"}
    return None


# ─────────────────────────────────────────────────
# SINGLE-STEP ROUTER (internal)
# ─────────────────────────────────────────────────

def _route_single(normalized: str) -> Dict:
    """Route a single normalized command string. Used internally by route_command."""

    if not normalized:
        return _build("noop", "", "Empty command.")

    logger.parsed(normalized)

    # ── 1. Greetings ──────────────────────────────────────────
    if normalized in _GREETINGS or any(normalized.startswith(g) for g in _GREETINGS):
        return _build("chat", normalized, "Greeting")

    # ── 1.2. Stop / Cancel (High Priority Reset) ──────────────
    if normalized in ("stop", "kill task", "shut up", "abort", "cancel", "stop everything", "reset"):
        return _build("stop", "", "Sir, I am stopping all current tasks.")

    # ── 1.5. Plugin/Skill System (Phase 26) — MOVE TO TOP ─────
    skill_match = match_skill(normalized)
    if skill_match:
        return _build(
            f"skill:{skill_match['skill_name']}",
            normalized,
            skill_match['description'],
        )

    # ── 2. File-spec (JSON patterns) ──────────────────────────
    file_cmd = _match_file_command(normalized)
    if file_cmd:
        return file_cmd

    # ── 3. Network-spec (JSON patterns) ───────────────────────
    net_cmd = _match_network_command(normalized)
    if net_cmd:
        return net_cmd

    # ── 4. n8n workflows ──────────────────────────────────────
    if normalized.startswith("send to telegram"):
        return _build("trigger_n8n", "send_to_telegram", "Running workflow")
    if normalized.startswith("backup file"):
        return _build("trigger_n8n", "backup_files", "Running workflow")
    wf = re.match(r"^run workflow\s+(.+)$", normalized)
    if wf:
        return _build("trigger_n8n", wf.group(1).strip(), "Running workflow")

    # ── 5. Navigation ─────────────────────────────────────────
    nav = re.match(r"^(?:go to|take me to|navigate to|open my)\s+(.+)$", normalized)
    if nav:
        target = nav.group(1).strip()
        ttype = _classify_target(target)
        if ttype == "url":
            return _build("open_dynamic", _resolve_url(target), f"Opening {target}",
                          extra={"resolved_type": "url"})
        return _build("open_folder", _resolve_folder(target), f"Opening {target}")

    # ── 6. Dynamic Open: open <target> on/in <app> ────────────
    open_with = re.match(
        r"^(?:open|launch|start)\s+(.+?)\s+(?:on|in|with|using)\s+(.+)$", normalized
    )
    if open_with:
        target = open_with.group(1).strip()
        app = open_with.group(2).strip()
        ttype = _classify_target(target)
        exe = _resolve_app(app)

        # Record app for context awareness
        session.record("open_dynamic", target, app=exe)

        if ttype in ("url", "unknown"):
            url = _resolve_url(target)
            return _build("open_dynamic", url, f"Opening {target} in {app}",
                          extra={"app": exe, "resolved_type": "url"})
        elif ttype == "file":
            return _build("open_dynamic", target, f"Opening {target} in {app}",
                          extra={"app": exe, "resolved_type": "file"})
        else:
            return _build("open_folder", _resolve_folder(target), f"Opening folder {target}")

    # ── 7. Open folder <name> ─────────────────────────────────
    folder_match = re.match(r"^(?:open|launch|start)\s+folder\s+(.+)$", normalized)
    if folder_match:
        target = folder_match.group(1).strip().strip("'\"")
        return _build("open_folder", _resolve_folder(target), f"Opening folder {target}")

    # ── 8. Open <target> (generic — dynamic type detection) ───
    open_generic = re.match(r"^(?:open|launch|start)\s+(.+)$", normalized)
    if open_generic:
        target = open_generic.group(1).strip()
        ttype = _classify_target(target)

        # Context awareness: if last command was a browser, reuse it
        ctx_app = session.get_context_app()

        if ttype == "url":
            url = _resolve_url(target)
            extra = {"resolved_type": "url"}
            if ctx_app and ctx_app in ("chrome", "msedge", "firefox", "brave"):
                extra["app"] = ctx_app
            session.record("open_dynamic", target)
            return _build("open_dynamic", url, f"Opening {target}", extra=extra)
        elif ttype == "file":
            extra = {"resolved_type": "file"}
            if ctx_app:
                extra["app"] = ctx_app
            return _build("open_dynamic", target, f"Opening file {target}", extra=extra)
        elif ttype == "folder":
            return _build("open_folder", _resolve_folder(target), f"Opening {target}")
        else:
            # Unknown: treat as app launch
            session.record("open_app", target, app=_resolve_app(target))
            return _build("open_app", target, f"Opening {target}")

    # ── 9. Media Controls ─────────────────────────────────────
    for phrase, action_key in _MEDIA_KEYWORDS.items():
        if re.search(rf"\b{re.escape(phrase)}\b", normalized):
            return _build("media_control", action_key, f"Executing: {action_key}")

    # ── 10. Power Controls ────────────────────────────────────
    if re.search(r"\b(lock|lock\s+(pc|computer|screen|workstation))\b", normalized):
        return _build("power_state", "lock", "Locking workstation")
    if re.search(r"\b(sleep|suspend|hibernate)\s*(pc|computer|laptop)?\b", normalized):
        return _build("power_state", "sleep", "Putting system to sleep")
    if re.search(r"\b(shutdown|shut down|power off|turn off)\s*(pc|computer|laptop)?\b", normalized):
        return _build("power_state", "shutdown", "Shutting down")
    if re.search(r"\b(restart|reboot)\s*(pc|computer|laptop)?\b", normalized):
        return _build("power_state", "restart", "Restarting")

    # ── 11. Vision / Screen ───────────────────────────────────
    if re.search(r"\b(capture screen|take screenshot|screenshot|what is on my screen|see my screen|what do you see)\b", normalized):
        return _build("capture_screen", "", "Capturing screen context")

    # ── 12. Web Search ────────────────────────────────────────
    search_match = re.match(
        r"^(?:search for|search the web for|search|what is|who is|look up|google|search google)\s+(.+)$",
        normalized
    )
    if search_match:
        q = search_match.group(1).strip()
        if q:
            return _build("quick_search", q, f"Searching web for: {q}")

    # ── 13. Close / Kill App ──────────────────────────────────
    close_match = re.match(r"^(?:close|kill|stop|terminate|exit)\s+(?:the\s+)?(?:app|application|process|program)?\s*(.+)$", normalized)
    if close_match:
        target = close_match.group(1).strip()
        if target.lower() == "it":
            # Co-reference resolution: find last app in session
            target = session.get_context_app() or "it"
        
        exe = _resolve_app(target)
        return _build("kill_process", exe, f"Closing {target}")

    # ── 14. Fallback → NLU Reasoner (Phase 6/26) ──────────
    logger.info(f"[ROUTER] No direct pattern match for '{normalized}'. Using NLU Reasoner...")
    try:
        from skills.system_agent import _generate_code
        # We repurpose the system_agent's logic to see if it can generate a script or if it's a creative request
        # For the stress test, we'll route complex/fuzzy intents to system_agent
        return _build("skill:system_agent", normalized, "Analyzing complex intent...")
    except Exception:
        pass

    return _build("unknown", "", "Command not recognized.")


# ─────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────

def route_command(text: str) -> Dict | List[Dict]:
    """
    Route a natural language command to structured action(s).

    Returns a single dict for simple commands, or a list of dicts
    for multi-step commands ("open chrome and search youtube").

    Includes LRU cache (Phase 11) and multi-step splitting (Phase 5).
    """
    # Phase 11: Check cache first
    cached = route_cache.get(text)
    if cached is not None:
        return cached

    logger.input(text)

    # Phase 5: Multi-step splitting
    steps = split_multi_step(text)

    if len(steps) <= 1:
        # Single command
        normalized = steps[0] if steps else ""
        result = _route_single(normalized)
        route_cache.put(text, result)
        return result
    else:
        # Multi-step: route each independently
        results = [_route_single(step) for step in steps]
        route_cache.put(text, results)
        return results
