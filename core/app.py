from __future__ import annotations

"""Application orchestration for JARVIS-X."""

import threading
import time
import json
from typing import Optional, Any, Dict, List

import config
from core.action_registry import ACTION_REGISTRY, execute_action
from core.command_router import route_command
from core.intent_engine import detect_intent, strip_wake_word
from core.validator import validate_action
from core.background_agent import BackgroundAgent
from core.startup import start_startup_sequence
from memory.memory_store import get_recent_history, get_relevant_context, save_interaction
from memory.response_cache import get_cached_response, put_cached_response
from memory.workflow_store import record_workflow
from skills import skill_registry
from triggers.clap_detector import ClapDetector
from ui.application import launch_ui
from voice.voice_input import VoiceListener
from utils.logger import get_logger
from utils import EventBus
from brain.ai_engine import interpret_command
from voice.tts_engine import speak

logger = get_logger(__name__)


class JarvisApp:
    """Main application controller for JARVIS-X."""

    def __init__(self, auto_start: bool = False) -> None:
        self.auto_start = auto_start
        self._activation_event = threading.Event()
        self._events = EventBus()
        self._events.subscribe("jarvis_wake", self._handle_activation)
        self._events.subscribe("command_received", self._handle_command)
        self._events.subscribe("background_suggestion", self._handle_background_suggestion)
        self._clap_detector = ClapDetector(event_bus=self._events)
        self._listener_thread: Optional[threading.Thread] = None
        self.voice = VoiceListener(self._events)
        self.stop_on_error: bool = True
        self._wake_engaged: bool = False
        self._background_agent = BackgroundAgent(self._events)

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
        self.voice.start()
        self._background_agent.start()
        try:
            launch_ui(self._events)
        except Exception as exc:  # noqa: BLE001
            logger.error("UI launch failed: %s", exc)
        if audio_thread and audio_thread.is_alive():
            audio_thread.join(timeout=0)
        end_ts = time.monotonic()
        logger.info("Cinematic startup completed in %.2fs", end_ts - start_ts)

    def _handle_background_suggestion(self, payload: dict) -> None:
        suggestions = payload.get("suggestions") or []
        if not suggestions:
            return
        message = "; ".join([item.get("message", "") for item in suggestions if item.get("message")])
        self._events.emit(
            "command_result",
            {"action": "background_suggestion", "type": "system", "message": message, "suggestions": suggestions},
        )



    def _handle_command(self, payload: dict) -> None:
        interaction_steps: List[Dict[str, Any]] = []
        final_result: Dict[str, Any] | None = None
        try:
            text_raw = payload.get("text", "") or ""
            source = payload.get("source", "ui")
            normalized, wake_used = strip_wake_word(text_raw)
            require_wake = config.REQUIRE_WAKE_WORD and source == "voice"
            if require_wake and not (wake_used or self._wake_engaged):
                msg = "Say 'Jarvis' to wake me before giving a command."
                result = {"action": "await_wake_word", "message": msg, "type": "system", "status": "pending"}
                self._events.emit("command_result", result)
                speak(msg)
                final_result = result
                return
            if wake_used:
                self._wake_engaged = True

            text = normalized or text_raw.lower().strip()
            if source == "voice":
                logger.info("[VOICE] %s", text)
            else:
                logger.info("[ROUTER] Received command: %s", text)

            if not text:
                return

            cached = get_cached_response(text)
            if cached:
                logger.info("[CACHE] Hit for '%s'", text)
                self._events.emit("command_result", cached)
                speak(cached.get("message", ""))
                final_result = cached
                return

            decision = detect_intent(text, {"source": source})
            if decision.needs_confirmation:
                confirm_msg = f"I heard '{text_raw}'. Should I run it? (confidence {decision.confidence:.2f})"
                result = {"action": "confirm_intent", "message": confirm_msg, "type": decision.source, "status": "pending"}
                self._events.emit("command_result", result)
                speak(confirm_msg)
                final_result = result
                return

            if decision.route == "macro":
                steps = decision.payload.get("steps", [])
                macro_results = self._execute_sequence(steps, text)
                interaction_steps = macro_results
                final_result = {
                    "action": "macro",
                    "type": "macro",
                    "steps": macro_results,
                    "message": "Macro executed",
                    "status": macro_results[-1].get("status") if macro_results else "success",
                }
            elif decision.route == "skill":
                skill = decision.payload.get("skill")
                skill_context = {"source": source, "payload": payload}
                skill_result = (
                    skill_registry.run(skill, text, skill_context)
                    if skill
                    else {"success": False, "status": "error", "message": "Skill missing"}
                )
                final_result = {"action": getattr(skill, "name", "skill"), "type": "skill", **skill_result}
                interaction_steps.append(
                    {
                        "action": final_result.get("action"),
                        "target": text,
                        "status": final_result.get("status"),
                        "output": final_result.get("output"),
                        "message": final_result.get("message"),
                    }
                )
            elif decision.route == "rule":
                route_result = decision.payload.get("route_result", {})
                final_result, interaction_steps = self._execute_route_result(route_result)
            else:
                history_entries = get_recent_history(limit=config.MAX_HISTORY_ENTRIES)
                relevant_entries = get_relevant_context(text, limit=config.MAX_RELEVANT_ENTRIES)
                final_result, interaction_steps = self._run_ai_path(text, history_entries, relevant_entries)

            if final_result:
                if final_result.get("message"):
                    speak(final_result.get("message", ""))
                self._events.emit("command_result", final_result)
                if final_result.get("status") not in ("error", "pending"):
                    put_cached_response(text, final_result)
        except Exception as exc:  # noqa: BLE001
            final_result = {"action": "error", "message": str(exc), "type": "error"}
            logger.error("Command handling failed: %s", exc)
            self._events.emit("command_result", final_result)
        finally:
            try:
                save_interaction(payload.get("text", ""), interaction_steps, final_result or {})
            except Exception as exc:  # noqa: BLE001
                logger.error("Memory persistence failed: %s", exc)

    def _execute_route_result(self, route_result: Dict[str, Any]) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
        action = route_result.get("action", "")
        target = route_result.get("target", "")
        extra = route_result.get("extra", {})
        if not action:
            return ({"action": "error", "message": "No action found", "type": "system"}, [])
        exec_result = self._execute_with_healing(action, target, extra)
        result = dict(route_result)
        result["exec_result"] = exec_result
        result["message"] = exec_result.get("message", route_result.get("message", ""))
        result["status"] = exec_result.get("status")
        steps = [
            {
                "action": action,
                "target": target,
                "status": exec_result.get("status"),
                "output": exec_result.get("output"),
                "message": exec_result.get("message"),
            }
        ]
        return result, steps

    def _run_ai_path(
        self, text: str, history_entries: List[Dict[str, Any]], relevant_entries: List[Dict[str, Any]]
    ) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
        ai_result = interpret_command(text, history=history_entries, relevant=relevant_entries)
        steps = ai_result.get("steps") or []
        if steps:
            validated = self._validate_ai_steps(steps)
            if "error" in validated:
                result = {"action": "ai_validation_error", "message": validated["error"], "type": "ai"}
                return result, []
            steps = validated["steps"]
            step_results = []
            previous = None
            for step in steps:
                exec_res = self._execute_step(step, previous_result=previous)
                step_results.append(exec_res)
                if not exec_res.get("success", True) and self.stop_on_error:
                    break
                previous = exec_res
            result = {
                "steps": step_results,
                "type": "ai",
                "message": ai_result.get("message", ""),
                "status": step_results[-1].get("status") if step_results else "success",
            }
            interactions = [
                {
                    "action": step.get("action", ""),
                    "target": step.get("target", ""),
                    "status": res.get("status"),
                    "output": res.get("output"),
                    "message": res.get("message"),
                }
                for step, res in zip(steps, step_results)
            ]
            return result, interactions
        return {
            "action": "unknown",
            "target": "",
            "message": ai_result.get("message", "No AI result"),
            "type": "ai",
            "status": "pending",
        }, []

    def _execute_sequence(self, steps: List[Any], original_text: str) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        previous: Optional[Dict[str, Any]] = None
        for step in steps:
            action = ""
            target = ""
            extra: Dict[str, Any] = {}
            if isinstance(step, str):
                routed = route_command(step)
                action = routed.get("action", "")
                target = routed.get("target", "")
                extra = routed.get("extra", {})
            elif isinstance(step, dict):
                action = step.get("action", "")
                target = step.get("target", "")
                extra = step.get("extra", {}) or {}
            if not action:
                continue
            exec_result = self._execute_with_healing(action, target, extra, previous_result=previous)
            results.append(
                {
                    "action": action,
                    "target": target,
                    "status": exec_result.get("status"),
                    "output": exec_result.get("output"),
                    "message": exec_result.get("message"),
                }
            )
            previous = exec_result
            if not exec_result.get("success", True) and self.stop_on_error:
                break
        if len(results) > 1:
            record_workflow(original_text, results)
        return results

    def _execute_with_healing(
        self,
        action: str,
        target: str = "",
        extra: Optional[Dict[str, Any]] = None,
        previous_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        extra = extra or {}
        validation = validate_action(action, target, extra)
        if not validation.get("ok"):
            return {"success": False, "status": "error", "message": validation.get("reason", "Validation failed")}

        result = execute_action(action, target, extra, previous_result=previous_result)
        if result.get("success"):
            return result

        for attempt in range(config.MAX_RETRY_ATTEMPTS):
            alt_target = self._build_alternative_target(action, target, attempt)
            if not alt_target or alt_target == target:
                continue
            logger.info("[EXECUTOR] Retry %s with %s", action, alt_target)
            retry = execute_action(action, alt_target, extra, previous_result=previous_result)
            if retry.get("success"):
                return retry

        ai_help = interpret_command(f"Find an alternative way to run {action} {target}", history=None, relevant=None)
        result["fallback"] = ai_help
        return result

    def _build_alternative_target(self, action: str, target: str, attempt: int) -> str:
        if action == "open_app":
            if attempt == 0 and not target.endswith(".exe"):
                return f"{target}.exe"
            if attempt == 1:
                return target.capitalize()
        if action == "open_url" and target and not target.startswith("http"):
            return f"https://{target}"
        return ""

    def _execute_step(self, step: dict, previous_result: Optional[dict] = None) -> dict:
        action = step.get("action", "")
        target = step.get("target", "") or (previous_result or {}).get("output", "")
        extra = step.get("extra", {})
        if not action:
            return {"success": False, "status": "error", "message": "Missing action"}
        return self._execute_with_healing(action, target, extra, previous_result=previous_result)

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
            if action not in ACTION_REGISTRY:
                return {"error": f"Unsupported action: {action}"}
            key = (action, target, json.dumps(extra, sort_keys=True, default=str))
            if key in seen:
                continue
            seen.add(key)
            deduped.append({"action": action, "target": target, "extra": extra})
        if not deduped:
            return {"error": "No valid steps"}
        return {"steps": deduped}

    def _shutdown(self) -> None:
        try:
            self._clap_detector.stop()
        except Exception as exc:  # noqa: BLE001
            logger.error("Error stopping clap detector: %s", exc)

        if hasattr(self, 'voice'):
            try:
                self.voice.stop()
            except Exception as exc:  # noqa: BLE001
                logger.error("Error stopping voice listener: %s", exc)

        try:
            self._background_agent.stop()
        except Exception as exc:  # noqa: BLE001
            logger.error("Error stopping background agent: %s", exc)
                
        if self._listener_thread and self._listener_thread.is_alive():
            self._listener_thread.join(timeout=0.2)
