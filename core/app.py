from __future__ import annotations

"""Application orchestration for JARVIS-X."""

import threading
import time
from typing import Optional

from core.action_registry import ACTION_REGISTRY, execute_action
from core.command_router import route_command
from core.startup import start_startup_sequence
from memory.memory_store import get_recent_history, get_relevant_context, save_interaction
from triggers.clap_detector import ClapDetector
from ui.application import launch_ui
from utils.logger import get_logger
from utils import EventBus
from brain.ai_engine import interpret_command

logger = get_logger(__name__)


class JarvisApp:
    """Main application controller for JARVIS-X."""

    def __init__(self, auto_start: bool = False) -> None:
        self.auto_start = auto_start
        self._activation_event = threading.Event()
        self._events = EventBus()
        self._events.subscribe("jarvis_wake", self._handle_activation)
        self._events.subscribe("command_received", self._handle_command)
        self._clap_detector = ClapDetector(event_bus=self._events)
        self._listener_thread: Optional[threading.Thread] = None
        self.stop_on_error: bool = True

    def _handle_activation(self) -> None:
        if self._activation_event.is_set():
            return
        logger.info("Double clap detected. Preparing cinematic startup...")
        self._activation_event.set()
        self._clap_detector.stop()

    def _start_clap_listener(self) -> None:
        def _runner() -> None:
            try:
                self._clap_detector.start()
            except Exception as exc:  # noqa: BLE001
                logger.error("Clap detector failed: %s", exc)

        self._listener_thread = threading.Thread(target=_runner, name="clap-listener", daemon=True)
        self._listener_thread.start()

    def run(self) -> None:
        """Start the assistant and wait for activation."""
        try:
            if self.auto_start:
                self._activation_event.set()
            else:
                logger.info("Listening for a double clap to start JARVIS-X...")
                self._start_clap_listener()

            self._activation_event.wait()
            self._start_cinematic_sequence()
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            self._shutdown()

    def _start_cinematic_sequence(self) -> None:
        start_ts = time.monotonic()
        audio_thread = start_startup_sequence()
        try:
            launch_ui(self._events)
        except Exception as exc:  # noqa: BLE001
            logger.error("UI launch failed: %s", exc)
        if audio_thread and audio_thread.is_alive():
            audio_thread.join(timeout=0)
        end_ts = time.monotonic()
        logger.info("Cinematic startup completed in %.2fs", end_ts - start_ts)

    def _handle_command(self, payload: dict) -> None:
        interaction_steps = []
        final_result = None
        try:
            text = payload.get("text", "")
            logger.info("Received command: %s", text)
            result = route_command(text)
            if result.get("action") == "unknown":
                history_entries = get_recent_history()
                relevant_entries = get_relevant_context(text)
                ai_result = interpret_command(text, history=history_entries, relevant=relevant_entries)
                steps = ai_result.get("steps") or []
                if steps:
                    step_results = []
                    previous = None
                    for step in steps:
                        exec_res = self._execute_step(step, previous_result=previous)
                        step_results.append(exec_res)
                        if not exec_res.get("success", True) and self.stop_on_error:
                            break
                        previous = exec_res
                    final_result = {"steps": step_results, "type": "ai"}
                    interaction_steps = [
                        {
                            "action": step.get("action", ""),
                            "target": step.get("target", ""),
                            "status": res.get("status"),
                            "output": res.get("output"),
                            "message": res.get("message"),
                        }
                        for step, res in zip(steps, step_results)
                    ]
                    self._events.emit("command_result", final_result)
                    return
                else:
                    result = {"action": "unknown", "target": "", "message": ai_result.get("message", "No AI result"), "type": "ai"}

            action = result.get("action", "")
            target = result.get("target", "")
            extra = result.get("extra", {})

            if action in ACTION_REGISTRY:
                logger.info("Executing action: %s target=%s", action, target)
                exec_result = execute_action(action, target, extra)
                result["exec_result"] = exec_result
                result["message"] = exec_result.get("message", result.get("message", ""))
                interaction_steps = [
                    {
                        "action": action,
                        "target": target,
                        "status": exec_result.get("status"),
                        "output": exec_result.get("output"),
                        "message": exec_result.get("message"),
                    }
                ]
            self._events.emit("command_result", result)
            final_result = result
        except Exception as exc:  # noqa: BLE001
            final_result = {"action": "error", "message": str(exc), "type": "error"}
            logger.error("Command handling failed: %s", exc)
        finally:
            try:
                save_interaction(payload.get("text", ""), interaction_steps, final_result or {})
            except Exception as exc:  # noqa: BLE001
                logger.error("Memory persistence failed: %s", exc)

    def _execute_step(self, step: dict, previous_result: Optional[dict] = None) -> dict:
        action = step.get("action", "")
        target = step.get("target", "") or (previous_result or {}).get("output", "")
        extra = step.get("extra", {})
        if not action:
            return {"success": False, "status": "error", "message": "Missing action"}
        return execute_action(action, target, extra, previous_result=previous_result)

    def _shutdown(self) -> None:
        try:
            self._clap_detector.stop()
        finally:
            if self._listener_thread and self._listener_thread.is_alive():
                self._listener_thread.join(timeout=0.2)
