from __future__ import annotations

"""
Application Orchestration for JARVIS-X Dexter Copilot.

Phase 5:  Multi-step command execution
Phase 6:  Context awareness (session context)
Phase 8:  Structured logging ([INPUT] [PARSED] [ACTION] [EXECUTION] [ERROR])
Phase 12: Universal AI fallback
"""

import threading
import time
import json
from typing import Optional, List

from core.action_registry import ACTION_REGISTRY, execute_action
from core.command_router import route_command
from core.command_parser import session
from core.command_cache import route_cache
from core.startup import start_startup_sequence
from memory.memory_store import get_recent_history, get_relevant_context, save_interaction
from triggers.clap_detector import ClapDetector
from ui.application import launch_ui
from voice.voice_input import VoiceListener
from utils.logger import get_logger
from utils import EventBus
from brain.ai_engine import interpret_command
from voice.tts_engine import speak

logger = get_logger(__name__)


class JarvisApp:
    """Main application controller for JARVIS-X Dexter Copilot."""

    def __init__(self, auto_start: bool = False) -> None:
        self.auto_start = auto_start
        self._activation_event = threading.Event()
        self._events = EventBus()
        self._events.subscribe("jarvis_wake", self._handle_activation)
        self._events.subscribe("command_received", self._handle_command)
        self._clap_detector = ClapDetector(event_bus=self._events)
        self._listener_thread: Optional[threading.Thread] = None
        self.voice = VoiceListener(self._events)
        self.stop_on_error: bool = True

    # ─── Activation ───────────────────────────────────────────

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
            except Exception as exc:
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
        self.voice.start()
        try:
            launch_ui(self._events)
        except Exception as exc:
            logger.error("UI launch failed: %s", exc)
        if audio_thread and audio_thread.is_alive():
            audio_thread.join(timeout=0)
        end_ts = time.monotonic()
        logger.info("Cinematic startup completed in %.2fs", end_ts - start_ts)

    # ─── Command Pipeline ────────────────────────────────────

    def _handle_command(self, payload: dict) -> None:
        """
        Master command handler with structured logging (Phase 8).

        Pipeline:
            [INPUT] → [PARSED] → [ACTION] → [EXECUTION] → memory save
        """
        interaction_steps = []
        final_result = None
        start = time.monotonic()

        try:
            text = payload.get("text", "")
            if text:
                text = text.lower().strip()

            # ── [INPUT] ──────────────────────────────────────
            source = payload.get("source", "text")
            logger.info("[INPUT] source=%s text='%s'", source, text)

            # ── [PARSED] ─────────────────────────────────────
            route_result = route_command(text)
            logger.info("[PARSED] result=%s", _summary(route_result))

            # Multi-step: route_command may return a list
            if isinstance(route_result, list):
                # Phase 5: execute each step sequentially
                self._execute_multi_step(route_result, text, payload)
                return

            # Single-step from here
            result = route_result
            action = result.get("action", "")

            # ── [PARSED] single-step ─────────────────────────
            logger.info("[PARSED] action=%s target='%s'", action, result.get("target", ""))

            # ── AI Fallback (Phase 12) ───────────────────────
            if action == "unknown":
                result, interaction_steps = self._handle_unknown(text, result)
                final_result = result
                self._events.emit("command_result", result)
                res_msg = result.get("message")
                if res_msg:
                    speak(res_msg)
                return

            # ── Chat (greeting) — speak immediately ──────────
            if action == "chat":
                exec_result = execute_action(action, result.get("target", ""))
                result["exec_result"] = exec_result
                result["message"] = exec_result.get("message", "")
                logger.info("[ACTION] chat → '%s'", exec_result.get("message", ""))
                self._events.emit("command_result", result)
                speak(exec_result.get("message", ""))
                final_result = result
                return

            # ── [ACTION] Execute known action ────────────────
            target = result.get("target", "")
            extra = result.get("extra", {})

            if action not in ("noop",):
                logger.info("[ACTION] Executing: %s target='%s'", action, target)
                exec_result = execute_action(action, target, extra)
                result["exec_result"] = exec_result
                result["message"] = exec_result.get("message", result.get("message", ""))

                # ── [EXECUTION] Log result ───────────────────
                logger.info("[EXECUTION] status=%s message='%s'",
                            exec_result.get("status"), exec_result.get("message", ""))

                interaction_steps = [{
                    "action": action,
                    "target": target,
                    "status": exec_result.get("status"),
                    "output": exec_result.get("output"),
                    "message": exec_result.get("message"),
                }]

                # Record in session for context awareness (Phase 6)
                session.record(action, target, app=extra.get("app"))

            self._events.emit("command_result", result)

            res_msg = result.get("message")
            if res_msg:
                speak(res_msg)

            final_result = result

        except Exception as exc:
            final_result = {"action": "error", "message": str(exc), "type": "error"}
            logger.error("[ERROR] Command handling failed: %s", exc, exc_info=True)
        finally:
            elapsed = time.monotonic() - start
            logger.info("[PERF] Command processed in %.3fs", elapsed)
            try:
                save_interaction(payload.get("text", ""), interaction_steps, final_result or {})
            except Exception as exc:
                logger.error("[ERROR] Memory persistence failed: %s", exc)

    # ─── Multi-Step Execution (Phase 5) ──────────────────────

    def _execute_multi_step(self, steps: List[dict], text: str, payload: dict) -> None:
        """Execute a list of routed command steps sequentially."""
        logger.info("[MULTI-STEP] Executing %d steps", len(steps))
        all_interaction_steps = []
        previous = None
        final_result = {"type": "multi_step", "steps": []}

        for i, step_result in enumerate(steps):
            action = step_result.get("action", "")
            target = step_result.get("target", "")
            extra = step_result.get("extra", {})

            logger.info("[MULTI-STEP %d/%d] action=%s target='%s'", i + 1, len(steps), action, target)

            if action == "unknown":
                step_result, _ = self._handle_unknown(text, step_result)
            elif action == "chat":
                exec_result = execute_action(action, target)
                step_result["exec_result"] = exec_result
                speak(exec_result.get("message", ""))
            elif action not in ("noop",):
                exec_result = execute_action(action, target, extra, previous_result=previous)
                step_result["exec_result"] = exec_result
                step_result["message"] = exec_result.get("message", step_result.get("message", ""))

                logger.info("[EXECUTION] step %d: status=%s", i + 1, exec_result.get("status"))

                all_interaction_steps.append({
                    "action": action, "target": target,
                    "status": exec_result.get("status"),
                    "output": exec_result.get("output"),
                    "message": exec_result.get("message"),
                })

                session.record(action, target, app=extra.get("app"))

                if not exec_result.get("success", True) and self.stop_on_error:
                    logger.warning("[MULTI-STEP] Step %d failed, stopping chain", i + 1)
                    break

                previous = exec_result

            final_result["steps"].append(step_result)

        self._events.emit("command_result", final_result)

        # Speak the last step's message
        last_msg = final_result["steps"][-1].get("message", "") if final_result["steps"] else ""
        if last_msg:
            speak(last_msg)

        try:
            save_interaction(payload.get("text", ""), all_interaction_steps, final_result)
        except Exception as exc:
            logger.error("[ERROR] Memory persistence failed: %s", exc)

    # ─── AI Fallback (Phase 12) ──────────────────────────────

    def _handle_unknown(self, text: str, result: dict) -> tuple:
        """Send unrecognized commands to AI for interpretation."""
        logger.info("[AI-FALLBACK] Sending to AI: '%s'", text)
        interaction_steps = []
        try:
            history_entries = get_recent_history()
            relevant_entries = get_relevant_context(text)
            ai_result = interpret_command(text, history=history_entries, relevant=relevant_entries)
            steps = ai_result.get("steps") or []

            if steps:
                validated = self._validate_ai_steps(steps)
                if "error" in validated:
                    result = {"action": "ai_error", "message": validated["error"], "type": "ai"}
                    return result, []

                step_results = []
                previous = None
                for step in validated["steps"]:
                    exec_res = self._execute_step(step, previous_result=previous)
                    step_results.append(exec_res)
                    if not exec_res.get("success", True) and self.stop_on_error:
                        break
                    previous = exec_res

                interaction_steps = [
                    {"action": s.get("action", ""), "target": s.get("target", ""),
                     "status": r.get("status"), "output": r.get("output"),
                     "message": r.get("message")}
                    for s, r in zip(validated["steps"], step_results)
                ]

                ai_msg = ai_result.get("message")
                if ai_msg:
                    speak(ai_msg)

                result = {"steps": step_results, "type": "ai",
                          "message": ai_result.get("message", "")}
            else:
                msg = ai_result.get("message", "I'm not sure how to handle that.")
                result = {"action": "unknown", "target": "", "message": msg, "type": "ai"}
        except Exception as exc:
            logger.error("[AI-FALLBACK] AI interpretation failed: %s", exc)
            result = {"action": "error", "message": f"AI failed: {exc}", "type": "error"}

        return result, interaction_steps

    # ─── Step Execution ──────────────────────────────────────

    def _execute_step(self, step: dict, previous_result: Optional[dict] = None) -> dict:
        action = step.get("action", "")
        target = step.get("target", "") or (previous_result or {}).get("output", "")
        extra = step.get("extra", {})
        if not action:
            return {"success": False, "status": "error", "message": "Missing action"}
        return execute_action(action, target, extra, previous_result=previous_result)

    def _validate_ai_steps(self, steps: list[dict]) -> dict:
        if not isinstance(steps, list):
            return {"error": "Invalid steps format"}
        deduped = []
        seen = set()
        for step in steps:
            if not isinstance(step, dict):
                continue
            action = (step.get("action") or "").strip()
            target = step.get("target") or ""
            extra = step.get("extra") or {}
            if not action:
                return {"error": "Step missing action"}
            if action not in ACTION_REGISTRY and action != "open_dynamic":
                return {"error": f"Unsupported action: {action}"}
            key = (action, target, json.dumps(extra, sort_keys=True, default=str))
            if key in seen:
                continue
            seen.add(key)
            deduped.append({"action": action, "target": target, "extra": extra})
        if not deduped:
            return {"error": "No valid steps"}
        return {"steps": deduped}

    # ─── Shutdown ────────────────────────────────────────────

    def _shutdown(self) -> None:
        # Log cache stats on shutdown
        stats = route_cache.stats
        logger.info("[PERF] Cache stats: %s", stats)

        try:
            self._clap_detector.stop()
        except Exception as exc:
            logger.error("Error stopping clap detector: %s", exc)

        if hasattr(self, 'voice'):
            try:
                self.voice.stop()
            except Exception as exc:
                logger.error("Error stopping voice listener: %s", exc)

        if self._listener_thread and self._listener_thread.is_alive():
            self._listener_thread.join(timeout=0.2)


def _summary(result) -> str:
    """Create a short log-friendly summary of a route result."""
    if isinstance(result, list):
        return f"[multi-step x{len(result)}]"
    return f"action={result.get('action')} target='{result.get('target', '')[:50]}'"
