from __future__ import annotations

"""Rule-based command router for system and file commands."""

import re
from typing import Dict

from core.command_spec import COMMAND_SPEC
from core.network_spec import NETWORK_SPEC

_STOP_WORDS = ("please", "jarvis", "hey jarvis")
_PLACEHOLDER_FIELDS = ("path", "name", "src", "dest", "new_name", "root_path")


def _normalize(text: str) -> str:
    cleaned = text.strip().lower()
    for word in _STOP_WORDS:
        cleaned = cleaned.replace(word, "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _build(action: str, target: str, message: str) -> Dict[str, str]:
    return {"action": action, "target": target, "message": message, "type": "system"}


def _clean(val: str) -> str:
    return val.strip().strip('"').strip("'")


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
        return {
            "action": action,
            "target": cleaned.get("name", ""),
            "extra": {"path": cleaned.get("path", "")},
            "type": "file",
            "message": "Creating folder",
        }
    if action == "delete_file":
        return {"action": action, "target": cleaned.get("path", ""), "extra": {}, "type": "file", "message": "Deleting file"}
    if action == "move_file":
        return {
            "action": action,
            "target": cleaned.get("dest", ""),
            "extra": {"source": cleaned.get("src", "")},
            "type": "file",
            "message": "Moving file",
        }
    if action == "copy_file":
        return {
            "action": action,
            "target": cleaned.get("dest", ""),
            "extra": {"source": cleaned.get("src", "")},
            "type": "file",
            "message": "Copying file",
        }
    if action == "rename_file":
        return {
            "action": action,
            "target": cleaned.get("path", ""),
            "extra": {"new_name": cleaned.get("new_name", "")},
            "type": "file",
            "message": "Renaming file",
        }
    if action == "search_file":
        return {
            "action": action,
            "target": cleaned.get("name", ""),
            "extra": {"root_path": cleaned.get("root_path", "")},
            "type": "file",
            "message": "Searching file",
        }
    if action == "file_info":
        return {"action": action, "target": cleaned.get("path", ""), "extra": {}, "type": "file", "message": "File info"}
    return {"action": "unknown", "target": "", "extra": {}, "type": "file", "message": "Unknown file command"}


def _match_file_command(normalized: str) -> Dict[str, str] | None:
    for spec in COMMAND_SPEC:
        action = spec.get("action", "")
        for phrase in spec.get("phrases", []):
            regex = _phrase_to_regex(phrase)
            match = regex.match(normalized)
            if match:
                return _build_file_command(action, match.groupdict())
    return None


def _build_network_command(action: str, groups: Dict[str, str], cmd_type: str) -> Dict[str, str]:
    cleaned = {k: _clean(v) for k, v in groups.items()}
    target = cleaned.get("url") or cleaned.get("path") or ""
    return {"action": action, "target": target, "extra": cleaned, "type": cmd_type, "message": "Processing network request"}


def _match_network_command(normalized: str) -> Dict[str, str] | None:
    for spec in NETWORK_SPEC:
        action = spec.get("action", "")
        cmd_type = spec.get("type", "network")
        for phrase in spec.get("phrases", []):
            regex = _phrase_to_regex(phrase)
            match = regex.match(normalized)
            if match:
                return _build_network_command(action, match.groupdict(), cmd_type)
    return None


def _build_n8n_command(target: str) -> Dict[str, str]:
    return {"action": "trigger_n8n", "target": target, "extra": {}, "type": "n8n", "message": f"Running workflow {target}"}


def route_command(text: str) -> Dict[str, str]:
    """Return a structured action dict for the given text command."""
    normalized = _normalize(text)

    if not normalized:
        return _build("noop", "", "Empty command.")

    file_cmd = _match_file_command(normalized)
    if file_cmd:
        return file_cmd

    net_cmd = _match_network_command(normalized)
    if net_cmd:
        return net_cmd

    if normalized.startswith("send to telegram"):
        return _build_n8n_command("send_to_telegram")

    if normalized.startswith("backup files") or normalized.startswith("backup file"):
        return _build_n8n_command("backup_files")

    workflow_match = re.match(r"^run workflow\s+(.+)$", normalized)
    if workflow_match:
        wf_name = workflow_match.group(1).strip()
        if wf_name:
            return _build_n8n_command(wf_name)

    # YouTube open variants
    if any(normalized.startswith(prefix) for prefix in ("open youtube", "launch youtube", "start youtube")) or "youtube.com" in normalized:
        return _build("open_url", "https://youtube.com", "Opening YouTube")

    # Chrome / browser launch
    if any(phrase in normalized for phrase in ("open chrome", "launch chrome", "start chrome")):
        return _build("open_app", "chrome", "Launching Chrome")

    # Open folder with dynamic path
    folder_match = re.match(r"^(open|launch|start)\s+folder\s+(.+)$", normalized)
    if folder_match:
        target = folder_match.group(2).strip().strip('"').strip("'")
        target = target or "~"
        return _build("open_folder", target, f"Opening folder {target}")

    # Generic open app
    generic_app = re.match(r"^(open|launch|start)\s+(.+)$", normalized)
    if generic_app:
        target = generic_app.group(2).strip()
        if target:
            return _build("open_app", target, f"Opening {target}")

    # Media Controls — natural language variants
    _MEDIA_KEYWORDS = {
        "play":         "play",
        "pause":        "pause",
        "stop":         "stop",
        "next":         "next",
        "previous":     "previous",
        "skip":         "next",
        "volume up":    "volume_up",
        "turn up":      "volume_up",
        "louder":       "volume_up",
        "volume down":  "volume_down",
        "turn down":    "volume_down",
        "quieter":      "volume_down",
        "mute":         "mute",
        "unmute":       "mute",
    }
    for phrase, action_key in _MEDIA_KEYWORDS.items():
        if re.search(rf"\b{re.escape(phrase)}\b", normalized):
            # Make sure it's not an 'open app' command that also contains these words
            if not re.match(r"^(open|launch|start)\b", normalized):
                return _build("media_control", action_key, f"Executing media control: {action_key}")

    # Power State — natural language variants
    if re.search(r"\b(lock|lock\s+(pc|computer|screen|workstation))\b", normalized):
        return _build("power_state", "lock", "Locking workstation")
    if re.search(r"\b(sleep|suspend|hibernate)\s*(pc|computer|laptop)?\b", normalized):
        return _build("power_state", "sleep", "Putting system to sleep")

    # Vision / Screen Capture
    if re.search(r"\b(capture screen|take screenshot|screenshot|what is on my screen|see my screen|what do you see)\b", normalized):
        return _build("capture_screen", "", "Capturing screen context")

    # Web Intelligence
    search_match = re.match(r"^(search for|search the web for|search|what is|who is|look up|google|search google)\s+(.+)$", normalized)
    if search_match:
        target = search_match.group(2).strip()
        if target:
            return _build("quick_search", target, f"Searching web for: {target}")

    return _build("unknown", "", "Command not recognized. Try 'open youtube' or 'pause music'.")
