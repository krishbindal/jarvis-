from __future__ import annotations

"""Rule-based command router for system and file commands."""

import re
from typing import Dict

from core.command_spec import COMMAND_SPEC

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
    return re.compile(rf"^{pattern}$", re.IGNORECASE)


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


def route_command(text: str) -> Dict[str, str]:
    """Return a structured action dict for the given text command."""
    normalized = _normalize(text)

    if not normalized:
        return _build("noop", "", "Empty command.")

    file_cmd = _match_file_command(normalized)
    if file_cmd:
        return file_cmd

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

    return _build("unknown", "", "Command not recognized. Try 'open youtube' or 'open folder <path>'.")
