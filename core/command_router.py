from __future__ import annotations

"""
Universal Dynamic Command Router for JARVIS-X Dexter Copilot.

Parses all natural language commands WITHOUT hardcoding specific sites or apps.
Supports patterns:
    open <target>
    open <target> on/in <app>
    go to <folder>
    play/pause/mute/skip
    lock/sleep
    search <query>
    hi/hello/how are you
"""

import re
from pathlib import Path
from typing import Dict, Optional

from core.command_spec import COMMAND_SPEC
from core.network_spec import NETWORK_SPEC

# ─────────────────────────────────────────────────
# NLP Pre-Processing
# ─────────────────────────────────────────────────

_STOP_WORDS = ("please", "jarvis", "hey jarvis", "okay jarvis", "ok jarvis")

_FILLER_PHRASES = (
    "can you ", "could you ", "would you ", "will you ",
    "i want you to ", "i need you to ", "i'd like you to ",
    "please ", "now ", "just ", "go ahead and ",
    "for me ", "kindly ", "try to ",
)

_PLACEHOLDER_FIELDS = ("path", "name", "src", "dest", "new_name", "root_path")

# Well-known site shortcuts → full URLs (extensible, not hardcoded logic)
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
}

# User-folder spoken shortcuts
_FOLDER_MAP = {
    "downloads": str(Path("~").expanduser() / "Downloads"),
    "desktop":   str(Path("~").expanduser() / "Desktop"),
    "documents": str(Path("~").expanduser() / "Documents"),
    "pictures":  str(Path("~").expanduser() / "Pictures"),
    "music":     str(Path("~").expanduser() / "Music"),
    "videos":    str(Path("~").expanduser() / "Videos"),
    "home":      str(Path("~").expanduser()),
}

# File extensions for target-type detection
_FILE_EXTS = (
    ".pdf", ".txt", ".docx", ".xlsx", ".pptx", ".csv",
    ".py", ".js", ".html", ".css", ".json", ".md",
    ".jpg", ".png", ".gif", ".mp4", ".mp3",
    ".zip", ".rar", ".exe", ".bat",
)

_FOLDER_KEYWORDS = (
    "folder", "directory", "dir",
)

# App launch identity map — spoken name → executable
_APP_MAP = {
    "chrome":   "chrome",
    "edge":     "msedge",
    "firefox":  "firefox",
    "brave":    "brave",
    "vscode":   "code",
    "vs code":  "code",
    "visual studio code": "code",
    "notepad":  "notepad",
    "explorer": "explorer",
    "cmd":      "cmd",
    "terminal": "wt",
    "powershell": "powershell",
    "word":     "winword",
    "excel":    "excel",
    "discord":  "discord",
    "spotify":  "spotify",
    "steam":    "steam",
    "vlc":      "vlc",
    "obs":      "obs64",
}

# Media + Power + Vision + Greeting keywords
_MEDIA_KEYWORDS = {
    "play": "play", "pause": "pause", "stop": "stop",
    "next": "next", "previous": "previous", "skip": "next",
    "volume up": "volume_up", "turn up": "volume_up", "louder": "volume_up",
    "volume down": "volume_down", "turn down": "volume_down", "quieter": "volume_down",
    "mute": "mute", "unmute": "mute",
    "resume": "play",
}

_GREETINGS = (
    "hi", "hello", "hey", "what's up", "whats up", "sup",
    "good morning", "good evening", "good afternoon",
    "how are you", "how r u", "how are u", "you there",
    "are you there", "wake up", "thanks", "thank you",
    "bye", "goodbye", "see you", "good night",
)


# ─────────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────────

def _normalize(text: str) -> str:
    cleaned = text.strip().lower()
    for word in _STOP_WORDS:
        cleaned = cleaned.replace(word, "")
    # Strip filler phrases from start
    changed = True
    while changed:
        changed = False
        for filler in _FILLER_PHRASES:
            if cleaned.startswith(filler):
                cleaned = cleaned[len(filler):]
                changed = True
                break
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _build(action: str, target: str, message: str, extra: Optional[dict] = None) -> Dict:
    result = {"action": action, "target": target, "message": message, "type": "system"}
    if extra:
        result["extra"] = extra
    return result


def _clean(val: str) -> str:
    return val.strip().strip('"').strip("'")


def _classify_target(target: str) -> str:
    """Dynamically detect what kind of target this is: url, file, folder, app, or query."""
    t = target.lower().strip()
    if t.startswith("http://") or t.startswith("https://"):
        return "url"
    if ".com" in t or ".org" in t or ".net" in t or ".io" in t or ".dev" in t or ".co" in t:
        return "url"
    if t in _SITE_SHORTCUTS:
        return "url"
    if any(t.endswith(ext) for ext in _FILE_EXTS):
        return "file"
    if t in _FOLDER_MAP or any(kw in t for kw in _FOLDER_KEYWORDS):
        return "folder"
    return "unknown"


def _resolve_url(target: str) -> str:
    """Convert a spoken target to a valid URL."""
    t = target.lower().strip()
    if t.startswith("http://") or t.startswith("https://"):
        return t
    if t in _SITE_SHORTCUTS:
        return _SITE_SHORTCUTS[t]
    if ".com" in t or ".org" in t or ".net" in t or ".io" in t or ".dev" in t or ".co" in t:
        return f"https://{t}" if not t.startswith("www.") else f"https://{t}"
    # Fallback: treat as Google search
    return f"https://www.google.com/search?q={target.replace(' ', '+')}"


def _resolve_folder(target: str) -> str:
    """Convert a spoken folder name to a real path."""
    t = target.lower().strip()
    # Strip trailing "folder"
    t = re.sub(r"\s*(folder|directory|dir)$", "", t).strip()
    return _FOLDER_MAP.get(t, target)


def _resolve_app(app_name: str) -> str:
    """Convert a spoken app name to an executable."""
    a = app_name.lower().strip()
    return _APP_MAP.get(a, a)


# ─────────────────────────────────────────────────
# Spec matchers (file/network commands from JSON)
# ─────────────────────────────────────────────────

def _phrase_to_regex(phrase: str) -> re.Pattern[str]:
    pattern = phrase.lower()
    pattern = re.escape(pattern)
    for field in _PLACEHOLDER_FIELDS:
        pattern = pattern.replace(r"\{" + field + r"\}", rf"(?P<{field}>.+)")
    pattern = pattern.replace(r"\ ", r"\s+")
    return re.compile(rf"{pattern}", re.IGNORECASE)


def _build_file_command(action: str, groups: Dict[str, str]) -> Dict[str, str]:
    cleaned = {k: _clean(v) for k, v in groups.items()}
    if action == "list_files":
        path = cleaned.get("path", "")
        return {"action": action, "target": path, "extra": {}, "type": "file", "message": f"Listing files in {path}"}
    if action == "create_folder":
        return {"action": action, "target": cleaned.get("name", ""), "extra": {"path": cleaned.get("path", "")}, "type": "file", "message": "Creating folder"}
    if action == "delete_file":
        return {"action": action, "target": cleaned.get("path", ""), "extra": {}, "type": "file", "message": "Deleting file"}
    if action == "move_file":
        return {"action": action, "target": cleaned.get("dest", ""), "extra": {"source": cleaned.get("src", "")}, "type": "file", "message": "Moving file"}
    if action == "copy_file":
        return {"action": action, "target": cleaned.get("dest", ""), "extra": {"source": cleaned.get("src", "")}, "type": "file", "message": "Copying file"}
    if action == "rename_file":
        return {"action": action, "target": cleaned.get("path", ""), "extra": {"new_name": cleaned.get("new_name", "")}, "type": "file", "message": "Renaming file"}
    if action == "search_file":
        return {"action": action, "target": cleaned.get("name", ""), "extra": {"root_path": cleaned.get("root_path", "")}, "type": "file", "message": "Searching file"}
    if action == "file_info":
        return {"action": action, "target": cleaned.get("path", ""), "extra": {}, "type": "file", "message": "File info"}
    return {"action": "unknown", "target": "", "extra": {}, "type": "file", "message": "Unknown file command"}


def _match_file_command(normalized: str) -> Dict[str, str] | None:
    for spec in COMMAND_SPEC:
        action = spec.get("action", "")
        for phrase in spec.get("phrases", []):
            regex = _phrase_to_regex(phrase)
            m = regex.match(normalized)
            if m:
                return _build_file_command(action, m.groupdict())
    return None


def _match_network_command(normalized: str) -> Dict[str, str] | None:
    for spec in NETWORK_SPEC:
        action = spec.get("action", "")
        cmd_type = spec.get("type", "network")
        for phrase in spec.get("phrases", []):
            regex = _phrase_to_regex(phrase)
            m = regex.match(normalized)
            if m:
                cleaned = {k: _clean(v) for k, v in m.groupdict().items()}
                target = cleaned.get("url") or cleaned.get("path") or ""
                return {"action": action, "target": target, "extra": cleaned, "type": cmd_type, "message": "Processing network request"}
    return None


# ─────────────────────────────────────────────────
# MAIN ROUTER
# ─────────────────────────────────────────────────

def route_command(text: str) -> Dict[str, str]:
    """Universal dynamic command router — NO hardcoded sites or apps."""
    normalized = _normalize(text)

    if not normalized:
        return _build("noop", "", "Empty command.")

    # ── 1. Greetings / Conversational ─────────────────────────────
    if normalized in _GREETINGS or any(normalized.startswith(g) for g in _GREETINGS):
        return _build("chat", normalized, "Hi! I'm Jarvis, your Dexter Copilot. How can I help you?")

    # ── 2. File-spec commands (COMMAND_SPEC patterns) ─────────────
    file_cmd = _match_file_command(normalized)
    if file_cmd:
        return file_cmd

    # ── 3. Network-spec commands (NETWORK_SPEC patterns) ──────────
    net_cmd = _match_network_command(normalized)
    if net_cmd:
        return net_cmd

    # ── 4. n8n workflow triggers ──────────────────────────────────
    if normalized.startswith("send to telegram"):
        return _build("trigger_n8n", "send_to_telegram", "Running workflow")
    if normalized.startswith("backup file"):
        return _build("trigger_n8n", "backup_files", "Running workflow")
    wf = re.match(r"^run workflow\s+(.+)$", normalized)
    if wf:
        return _build("trigger_n8n", wf.group(1).strip(), f"Running workflow {wf.group(1)}")

    # ── 5. Navigation: "go to downloads", "take me to desktop" ───
    nav = re.match(r"^(?:go to|take me to|navigate to|open my)\s+(.+)$", normalized)
    if nav:
        target = nav.group(1).strip()
        target_type = _classify_target(target)
        if target_type == "url":
            return _build("open_dynamic", _resolve_url(target), f"Opening {target}",
                          extra={"resolved_type": "url"})
        real_path = _resolve_folder(target)
        return _build("open_folder", real_path, f"Opening {target}")

    # ── 6. DYNAMIC OPEN PARSER ────────────────────────────────────
    # Pattern: open <target> on/in/with <app>
    open_with = re.match(
        r"^(?:open|launch|start)\s+(.+?)\s+(?:on|in|with|using)\s+(.+)$",
        normalized
    )
    if open_with:
        target = open_with.group(1).strip()
        app    = open_with.group(2).strip()
        target_type = _classify_target(target)

        if target_type == "url":
            url = _resolve_url(target)
            exe = _resolve_app(app)
            return _build("open_dynamic", url, f"Opening {target} in {app}",
                          extra={"app": exe, "resolved_type": "url"})
        elif target_type == "file":
            exe = _resolve_app(app)
            return _build("open_dynamic", target, f"Opening {target} in {app}",
                          extra={"app": exe, "resolved_type": "file"})
        elif target_type == "folder":
            return _build("open_folder", _resolve_folder(target), f"Opening folder {target}")
        else:
            # Could be an app or unknown. Try URL first, then app
            url = _resolve_url(target)
            exe = _resolve_app(app)
            return _build("open_dynamic", url, f"Opening {target} in {app}",
                          extra={"app": exe, "resolved_type": "url"})

    # Pattern: open folder <name>
    folder_match = re.match(r"^(?:open|launch|start)\s+folder\s+(.+)$", normalized)
    if folder_match:
        target = folder_match.group(1).strip().strip("'\"")
        return _build("open_folder", _resolve_folder(target), f"Opening folder {target}")

    # Pattern: open <target>  (generic — dynamic type detection)
    open_generic = re.match(r"^(?:open|launch|start)\s+(.+)$", normalized)
    if open_generic:
        target = open_generic.group(1).strip()
        target_type = _classify_target(target)

        if target_type == "url":
            return _build("open_dynamic", _resolve_url(target), f"Opening {target}",
                          extra={"resolved_type": "url"})
        elif target_type == "file":
            return _build("open_dynamic", target, f"Opening file {target}",
                          extra={"resolved_type": "file"})
        elif target_type == "folder":
            return _build("open_folder", _resolve_folder(target), f"Opening {target}")
        else:
            # Unknown type → treat as an app
            return _build("open_app", target, f"Opening {target}")

    # ── 7. Media Controls ─────────────────────────────────────────
    for phrase, action_key in _MEDIA_KEYWORDS.items():
        if re.search(rf"\b{re.escape(phrase)}\b", normalized):
            return _build("media_control", action_key, f"Executing: {action_key}")

    # ── 8. Power Controls ─────────────────────────────────────────
    if re.search(r"\b(lock|lock\s+(pc|computer|screen|workstation))\b", normalized):
        return _build("power_state", "lock", "Locking workstation")
    if re.search(r"\b(sleep|suspend|hibernate)\s*(pc|computer|laptop)?\b", normalized):
        return _build("power_state", "sleep", "Putting system to sleep")

    # ── 9. Vision / Screen ────────────────────────────────────────
    if re.search(r"\b(capture screen|take screenshot|screenshot|what is on my screen|see my screen|what do you see)\b", normalized):
        return _build("capture_screen", "", "Capturing screen context")

    # ── 10. Web Search ────────────────────────────────────────────
    search_match = re.match(r"^(?:search for|search the web for|search|what is|who is|look up|google|search google)\s+(.+)$", normalized)
    if search_match:
        q = search_match.group(1).strip()
        if q:
            return _build("quick_search", q, f"Searching web for: {q}")

    # ── 11. Fallback → AI ────────────────────────────────────────
    return _build("unknown", "", "Command not recognized.")
