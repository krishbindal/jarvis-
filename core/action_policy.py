"""Fail-closed, one-action-at-a-time user approvals for consequential tools.

An LLM-supplied dictionary field cannot approve an action. Approval responses
are accepted only for outstanding random request IDs, intended to be delivered
from the Qt confirmation dialog. This is an application-level guard, not an
operating-system sandbox against arbitrary Python execution.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import secrets
import threading
from typing import Any, Dict

from utils.logger import get_logger

logger = get_logger(__name__)
APPROVAL_TIMEOUT_S = 45

# Default deny: code, webhooks, nontrivial file changes, and system side effects.
CONFIRM_ACTIONS = frozenset({
    "delete_file", "move_file", "copy_file", "rename_file", "create_folder",
    "download_file", "download_video", "convert_to_mp3", "convert_to_pdf",
    "trigger_n8n", "power_state", "kill_process", "execute_python",
    "open_executable",
    "click_element", "capture_screen", "automation:click", "automation:type", "automation:press_key",
    "automation:download",
})


def needs_approval(action: str) -> bool:
    return (
        action in CONFIRM_ACTIONS
        or action.startswith("mcp:")
        or action.startswith("skill:")
    )


@dataclass
class _Pending:
    requested_action: str
    done: threading.Event = field(default_factory=threading.Event)
    allowed: bool = False


class ActionApprovalManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._bus = None
        self._ui_ready = False
        self._pending: dict[str, _Pending] = {}

    def configure(self, event_bus) -> None:
        self.cancel_all()
        with self._lock:
            self._bus = event_bus
            self._ui_ready = False

    def set_ui_ready(self, ready: bool) -> None:
        with self._lock:
            self._ui_ready = bool(ready)
        if not ready:
            self.cancel_all()

    def request(self, action: str, target: Any = "") -> bool:
        if not needs_approval(action):
            return True
        # Never block the Qt event loop waiting for a dialog on the same thread.
        if threading.current_thread() is threading.main_thread():
            logger.warning("[APPROVAL] Denied %s: action called on main thread", action)
            return False
        with self._lock:
            if not self._ui_ready or self._bus is None:
                logger.warning("[APPROVAL] Denied %s: no interactive UI", action)
                return False
            ticket = secrets.token_urlsafe(24)
            pending = _Pending(requested_action=action)
            self._pending[ticket] = pending
            bus = self._bus

        # Do not expose generated scripts or email/clipboard bodies in logs.
        if action == "execute_python" or action.startswith("skill:system_agent"):
            summary = f"<{len(str(target))} characters of source/instructions>"
        else:
            summary = str(target).replace("\r", " ").replace("\n", " ")[:180]
        try:
            bus.emit("action_approval_requested", {
                "request_id": ticket, "action": action, "summary": summary,
            })
        except Exception:
            logger.error("[APPROVAL] Unable to request confirmation", exc_info=True)
        pending.done.wait(timeout=APPROVAL_TIMEOUT_S)
        with self._lock:
            self._pending.pop(ticket, None)
        logger.info("[APPROVAL] %s %s", "Allowed" if pending.allowed else "Denied", action)
        return bool(pending.allowed)

    def respond(self, request_id: str, allowed: bool) -> bool:
        """Called by the trusted Qt dialog after a user click."""
        with self._lock:
            pending = self._pending.get(request_id)
            if pending is None or pending.done.is_set() or not self._ui_ready:
                return False
            pending.allowed = allowed is True
            pending.done.set()
            return True

    def cancel_all(self) -> None:
        with self._lock:
            items = list(self._pending.values())
            self._pending.clear()
        for pending in items:
            pending.allowed = False
            pending.done.set()


_manager = ActionApprovalManager()


def get_action_approvals() -> ActionApprovalManager:
    return _manager


def check_action(action: str, target: Any = "") -> Dict[str, Any] | None:
    """Return a denial payload or None if the action can proceed."""
    if not needs_approval(action):
        return None
    if get_action_approvals().request(action, target):
        return None
    return {
        "success": False,
        "status": "approval_required",
        "message": f"{action} was not approved. Open Jarvis and explicitly confirm the action to proceed.",
    }
