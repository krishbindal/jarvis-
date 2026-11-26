"""Conservative checks for untrusted AI-proposed open targets."""
from __future__ import annotations

from pathlib import PurePath
from urllib.parse import urlsplit

_DANGEROUS_SCHEMES = (
    "javascript:", "data:", "vbscript:", "shell:", "ms-settings:",
    "powershell:", "command:", "ms-excel:", "ms-word:",
)
_EXECUTABLE_SUFFIXES = frozenset({
    ".exe", ".bat", ".cmd", ".ps1", ".vbs", ".vbe", ".js", ".jse",
    ".msi", ".scr", ".com", ".lnk", ".hta",
})


def inspect_open_target(target: object, resolved_type: object) -> tuple[bool, bool, str]:
    """(allowed, requires_confirmation, reason) for OS/browser opening."""
    if not isinstance(target, str) or not target.strip() or len(target) > 2048:
        return False, False, "Open target must be nonempty text under 2049 characters."
    if any(char in target for char in ("\0", "\r", "\n")):
        return False, False, "Open target contains control characters."
    value = target.strip()
    low = value.lower()
    if low.startswith(_DANGEROUS_SCHEMES):
        return False, False, "Potentially executable URI schemes are not supported."

    kind = resolved_type if isinstance(resolved_type, str) else ""
    if kind == "url":
        parsed = urlsplit(value)
        if parsed.scheme.lower() not in ("https", "http") or not parsed.netloc:
            return False, False, "Only explicit http:// and https:// URLs are supported."
        if parsed.username is not None or parsed.password is not None:
            return False, False, "URLs embedding credentials are not permitted."
        return True, False, ""

    # Opening executable local files is an action that requires explicit consent.
    # Windows backslash paths need their own suffix handling even on Linux CI.
    filename = value.replace("\\", "/").rstrip("/").rsplit("/", 1)[-1]
    suffix = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if suffix in _EXECUTABLE_SUFFIXES:
        return True, True, "Opening this file may execute code."
    return True, False, ""
