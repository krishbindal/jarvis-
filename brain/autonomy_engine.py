from __future__ import annotations

"""
Autonomy Engine (Phase 30+)

Background observer that:
- Watches active apps/time to learn habits
- Detects repeated patterns and proposes routines
- Executes safe scheduled tasks with self-healing fallbacks
- Respects context (no spam while user is busy)
- Allows interruption via EventBus ("interrupt_autonomy")
"""

import time
import threading
from collections import deque
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from core.context_state import ContextState
from memory.memory_store import (
    log_observation,
    record_pattern,
    mark_pattern_suggested,
    due_tasks,
    mark_task_run,
)
from utils.logger import get_logger
from utils.system_context import (
    get_active_process_name,
    get_active_window_title,
    get_system_stats,
)

logger = get_logger(__name__)

try:
    from core.action_registry import execute_action  # type: ignore
except Exception:  # noqa: BLE001
    execute_action = None


class AutonomyEngine:
    """Runs lightweight observation + habit detection in the background."""

    def __init__(self, event_bus, context: ContextState) -> None:
        self._bus = event_bus
        self._context = context
        self._running = False
        self._interrupted = False
        self._thread: Optional[threading.Thread] = None
        self._sequence = deque(maxlen=5)
        self._last_app = ""
        self._cooldown: Dict[str, float] = {}
        self._last_command: Optional[str] = None
        self._interval = 6  # seconds; keep light for performance

        self._bus.subscribe("command_received", self._on_command)
        self._bus.subscribe("interrupt_autonomy", self._on_interrupt)
        self._bus.subscribe("system_shutdown", lambda *_: self.stop())

    # ─── Lifecycle ───────────────────────────────────────────

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._interrupted = False
        self._thread = threading.Thread(target=self._loop, daemon=True, name="autonomy-engine")
        self._thread.start()
        logger.info("[AUTONOMY] Engine online.")

    def stop(self) -> None:
        self._running = False
        self._interrupted = True
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.5)
        logger.info("[AUTONOMY] Engine stopped.")

    def _on_interrupt(self, *_args, **_kwargs) -> None:
        """External interrupt (user stop)."""
        self._interrupted = True
        logger.info("[AUTONOMY] Interruption requested; pausing autonomous actions.")

    # ─── Observing ───────────────────────────────────────────

    def _loop(self) -> None:
        time.sleep(2.0)  # allow startup to finish
        while self._running:
            try:
                self._observe_active_app()
                self._detect_pattern()
                self._check_schedules()
            except Exception as exc:  # noqa: BLE001
                logger.error("[AUTONOMY] Loop error: %s", exc)
            time.sleep(self._interval)

    def _observe_active_app(self) -> None:
        app = (get_active_process_name() or "").lower()
        title = get_active_window_title()
        if not app:
            return
        if app != self._last_app:
            log_observation("active_app", app, {"window": title})
            self._sequence.append(app)
            self._last_app = app

        # Periodically capture coarse context to feed the AI brain/memory
        stats = get_system_stats()
        if stats:
            log_observation("system", "heartbeat", stats)

    def _on_command(self, payload: dict) -> None:
        text = (payload or {}).get("text", "")
        if not text:
            return
        source = (payload or {}).get("source", "command")
        log_observation("command", text.lower(), {"source": source})
        self._last_command = text.lower().strip()
        # Commands influence pattern memory too
        self._sequence.append(f"cmd:{source}")

    # ─── Pattern Detection & Suggestions ─────────────────────

    def _detect_pattern(self) -> None:
        """Persist patterns and surface helpful suggestions."""
        if len(self._sequence) < 3:
            return

        recent = list(self._sequence)[-3:]
        label = self._label_pattern(recent)
        stats = record_pattern(recent, label)
        if not stats:
            return

        # Avoid spamming suggestions; only propose when count crosses threshold and not too recent
        pattern_key = "|".join(recent)
        now = time.time()
        last_suggested = stats.get("last_suggested")
        if stats.get("count", 0) < 3:
            return
        if self._cooldown.get(pattern_key, 0) > now:
            return
        if last_suggested:
            try:
                # 5 minute quiet window
                last_ts = datetime.fromisoformat(last_suggested).timestamp()
                if now - last_ts < 300:
                    return
            except Exception:
                pass

        if self._context.task_in_progress:
            logger.debug("[AUTONOMY] Suppressing suggestion; task in progress.")
            return

        suggestion = self._build_suggestion(label, recent)
        self._emit_suggestion(suggestion, recent)
        self._cooldown[pattern_key] = now + 600  # 10 minute cooldown
        mark_pattern_suggested(recent)

    def _label_pattern(self, seq: List[str]) -> str:
        joined = " ".join(seq)
        if "youtube" in joined or "music" in joined or "spotify" in joined:
            return "entertainment mode"
        if any(item for item in seq if "code" in item or "terminal" in item or "pycharm" in item):
            return "dev sprint"
        if any(item for item in seq if "teams" in item or "zoom" in item or "outlook" in item):
            return "meeting prep"
        if any(item for item in seq if "notion" in item or "onenote" in item):
            return "planning loop"
        return f"{seq[-1]} focus"

    def _build_suggestion(self, label: str, seq: List[str]) -> dict:
        # Craft friendly, minimal message
        prep = ", ".join(seq)
        command = self._build_command(seq)
        msg = f"Sir, I've spotted your '{label}' routine ({prep}). Want me to prepare it now?"
        return {
            "message": msg,
            "label": label,
            "command": command,
            "sequence": seq,
            "auto_execute": False,  # suggestions require confirmation
        }

    def _build_command(self, seq: List[str]) -> str:
        # Map common apps to URLs or names for routing clarity
        mapped: List[str] = []
        for item in seq:
            if "youtube" in item:
                mapped.append("https://www.youtube.com")
            elif "music" in item or "spotify" in item:
                mapped.append("spotify")
            else:
                mapped.append(item)
        # Natural instruction so the router can split into steps
        if len(mapped) == 3:
            return f"open {mapped[0]}, then go to {mapped[1]}, and start {mapped[2]}"
        return " and then ".join([f"open {m}" for m in mapped])

    def _emit_suggestion(self, payload: dict, seq: List[str]) -> None:
        try:
            self._bus.emit("autonomy_suggestion", payload)
            logger.info("[AUTONOMY] Suggestion emitted for pattern %s", seq)
        except Exception as exc:  # noqa: BLE001
            logger.error("[AUTONOMY] Failed to emit suggestion: %s", exc)

    # ─── Scheduler & Auto Tasks ──────────────────────────────

    def _check_schedules(self) -> None:
        pending = due_tasks()
        if not pending:
            return

        now = datetime.now()
        for task in pending:
            task_id = task["id"]
            label = task.get("label", "task")
            command = task.get("command", "")
            recur = task.get("recur_seconds", 0)
            auto = bool(task.get("auto_execute"))

            if self._context.task_in_progress and not auto:
                logger.debug("[AUTONOMY] Deferring '%s' because a task is active.", label)
                continue

            # Context-aware: avoid re-opening an app already active
            if self._context.current_app and self._context.current_app.lower() in command.lower():
                logger.debug("[AUTONOMY] Skipping '%s' because it is already active.", label)
                mark_task_run(task_id, status="completed")
                continue

            if auto and not self._interrupted:
                logger.info("[AUTONOMY] Auto-running scheduled task '%s'", label)
                success = self._execute_safe_command(command)
                if recur and success:
                    mark_task_run(task_id, status="recurring")
                else:
                    mark_task_run(task_id, status="completed" if success else "failed")
            else:
                message = f"Reminder: '{label}' is scheduled now. Shall I handle it?"
                self._bus.emit("autonomy_suggestion", {
                    "message": message,
                    "label": label,
                    "command": command,
                    "auto_execute": False,
                })
                mark_task_run(task_id, status="waiting_confirmation")

    # ─── Execution Helpers ───────────────────────────────────

    def _execute_safe_command(self, command: str) -> bool:
        """Execute via action registry with self-healing fallbacks."""
        try:
            if execute_action is None:
                self._bus.emit("command_received", {"text": command, "source": "autonomy"})
                return True
            # Heuristic: if command resembles 'open <target>' try direct action to keep it deterministic
            lowered = command.lower()
            if lowered.startswith("open "):
                target = command.split(" ", 1)[1].strip()
                if self._context.current_app and target.lower() in (self._context.current_app or "").lower():
                    logger.info("[AUTONOMY] %s already active; skipping.", target)
                    return True
                result = execute_action("open_app", target)
                if not result.get("success", True):
                    result = execute_action("open_dynamic", target, {"resolved_type": "app"})
                self._context.update_after_action("open_app", target, {}, result)
                return bool(result.get("success", False))

            # Fallback: let the main pipeline parse the natural command
            self._bus.emit("command_received", {"text": command, "source": "autonomy"})
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("[AUTONOMY] Command execution failed: %s", exc)
            return False


_autonomy_engine: Optional[AutonomyEngine] = None


def get_autonomy_engine(event_bus=None, context: ContextState | None = None) -> AutonomyEngine:
    """Singleton accessor to avoid duplicate background loops."""
    global _autonomy_engine
    if _autonomy_engine is None:
        if event_bus is None or context is None:
            raise ValueError("event_bus and context are required to start AutonomyEngine")
        _autonomy_engine = AutonomyEngine(event_bus, context)
    return _autonomy_engine
