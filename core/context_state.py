from __future__ import annotations

"""Thread-safe global context for cross-command continuity."""

import threading
from typing import Dict, Optional

from utils.system_context import get_active_window_title, get_active_process_name


class ContextState:
    """Stores coarse session context to enable follow-up reasoning."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._state: Dict[str, Optional[str]] = {
            "current_app": None,
            "current_url": None,
            "last_action": None,
            "last_user_intent": None,
            "last_result_message": None,
            "last_result_status": None,
            "task_in_progress": False,
        }

    def snapshot(self) -> Dict[str, Optional[str]]:
        with self._lock:
            snap = dict(self._state)
        snap["active_window"] = get_active_window_title()
        snap["active_process"] = get_active_process_name()
        return snap

    def set_intent(self, intent: str) -> None:
        with self._lock:
            self._state["last_user_intent"] = intent

    def update_after_action(self, action: str, target: str, extra: Optional[dict], exec_result: Optional[dict]) -> None:
        with self._lock:
            self._state["last_action"] = action
            if exec_result:
                self._state["last_result_message"] = exec_result.get("message")
                self._state["last_result_status"] = exec_result.get("status")
            if action in ("open_app", "open_dynamic", "open_url"):
                app = (extra or {}).get("app") or target
                self._state["current_app"] = app
            if action in ("open_dynamic", "open_url") and target:
                self._state["current_url"] = target
            if action == "kill_process":
                killed = target.lower()
                if self._state.get("current_app") and killed in (self._state["current_app"] or "").lower():
                    self._state["current_app"] = None
            if exec_result and exec_result.get("success") is False:
                self._state["task_in_progress"] = False

    def set_task(self, value: bool) -> None:
        with self._lock:
            self._state["task_in_progress"] = value

    @property
    def current_app(self) -> Optional[str]:
        with self._lock:
            return self._state.get("current_app")

    @property
    def current_url(self) -> Optional[str]:
        with self._lock:
            return self._state.get("current_url")

    def has_active_context(self) -> bool:
        with self._lock:
            return bool(self._state.get("current_app") or self._state.get("current_url"))

    @property
    def task_in_progress(self) -> bool:
        with self._lock:
            return bool(self._state.get("task_in_progress"))

    @property
    def last_action(self) -> Optional[str]:
        with self._lock:
            return self._state.get("last_action")

    @property
    def last_user_intent(self) -> Optional[str]:
        with self._lock:
            return self._state.get("last_user_intent")
