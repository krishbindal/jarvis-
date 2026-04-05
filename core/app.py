from __future__ import annotations

"""
Application Orchestration for JARVIS-X Dexter Copilot.

Phase 5:  Multi-step command execution
Phase 6:  Context awareness (session context)
Phase 8:  Structured logging ([INPUT] [PARSED] [ACTION] [EXECUTION] [ERROR])
Phase 12: Universal AI fallback
Phase 16: Multimodal Vision (background screen awareness)
Phase 17: Floating Overlay HUD
Phase 18: Premium Edge-TTS with overlay state signaling
Phase 19: Proactive Intelligence loop
Phase 20: "Hey Jarvis" Wake Word
Phase 22: Clipboard Intelligence
Phase 26: Plugin/Skill System
Phase 27: Conversation Personality
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
from memory.personality import get_personality_context, learn_from_interaction
from triggers.clap_detector import ClapDetector
from triggers.wake_word import WakeWordDetector
from triggers.clipboard_monitor import ClipboardMonitor
from triggers.system_monitor import SystemMonitor
from triggers.file_sorcerer import FileSorcerer
from triggers.knowledge_indexer import KnowledgeIndexer
from triggers.sentinel_fixer import SentinelFixer
from ui.application import launch_ui
from voice.voice_input import VoiceListener
from utils.logger import get_logger
from utils import EventBus
from brain.ai_engine import interpret_command
from brain.vision_provider import get_vision_provider
from brain.researcher import DeepResearchAgent
from brain.proactive_engine import get_proactive_engine
from voice.tts_engine import speak, init_tts
from memory.database import MemoryDB
from core.interaction_loop import InteractionLoop
from core.mcp_hub import get_mcp_hub
from core.context_state import ContextState
from brain.agent_planner import plan_steps
from executor import agent_tools

logger = get_logger(__name__)


class JarvisApp:
    """Main application controller for JARVIS-X Dexter Copilot."""

    def __init__(self, auto_start: bool = False) -> None:
        self.auto_start = auto_start
        self._running = True
        self._activation_event = threading.Event()
        self._events = EventBus()
        self._events.subscribe("jarvis_wake", self._handle_activation)
        self._events.subscribe("command_received", self._handle_command)
        self._events.subscribe("proactive_warning", lambda msg: speak(msg))
        
        self._clap_detector = ClapDetector(event_bus=self._events)
        self._sys_monitor = SystemMonitor(event_bus=self._events)
        self._listener_thread: Optional[threading.Thread] = None
        self.voice = VoiceListener(self._events)
        self.stop_on_error: bool = True

        # Phase 16: Vision Provider
        self._vision = get_vision_provider()

        # Phase 18: Initialize TTS with event bus for overlay integration
        init_tts(event_bus=self._events)

        # Phase 19: Proactivity control
        self._proactive_thread: Optional[threading.Thread] = None
        self._proactive_running = False

        # Phase 20: Wake Word Detector
        self._wake_word = WakeWordDetector(event_bus=self._events)

        # Phase 22: Clipboard Monitor
        self._clipboard = ClipboardMonitor(event_bus=self._events)

        # Phase 23: File Sorcerer
        self._sorcerer = FileSorcerer(event_bus=self._events)
        
        # Phase 26: Knowledge Indexer (Omniscient)
        self._indexer = KnowledgeIndexer()

        # Phase 26: Deep Research Agent
        self._researcher = DeepResearchAgent(event_bus=self._events)
        
        # Phase 26: Sentinel Fixer (Self-Healing)
        self._sentinel = SentinelFixer(event_bus=self._events)
        
        # Database for stats
        self._db = MemoryDB()
        self._interactions = InteractionLoop(self._events)
        self._context = ContextState()
        self._events.subscribe("interrupt_tts", lambda *_: self._interactions.stop())

        # Phase 26: Start MCP Hub (Open Interpreter, Playwright, etc.)
        try:
            self._mcp_hub = get_mcp_hub()
            threading.Thread(target=self._mcp_hub.start, name="mcp-hub", daemon=True).start()
        except Exception as exc:
            logger.error("Failed to start MCP Hub: %s", exc)

    # ─── Activation ───────────────────────────────────────────

    def _handle_activation(self) -> None:
        if self._activation_event.is_set():
            return
        logger.info("Wake signal detected. Preparing cinematic startup...")
        self._activation_event.set()
        self._clap_detector.stop()
        self._wake_word.stop()

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
                logger.info("Listening for 'Hey Jarvis' or double clap...")
                self._start_clap_listener()
                self._wake_word.start()  # Phase 20

            # Wait for activation
            self._activation_event.wait()
            self._start_cinematic_sequence()

            # Keep the main thread alive for background services
            # This ensures that even if the UI closes or fails, the voice listener,
            # proactive engine, and other background threads keep running.
            logger.info("Application entering resident mode. Press Ctrl+C to stop.")
            while self._running:
                time.sleep(1)

        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            self._shutdown()

    def _start_cinematic_sequence(self) -> None:
        start_ts = time.monotonic()
        audio_thread = start_startup_sequence()
        self.voice.start()
        try:
            self._events.emit("cinematic_log", {"text": "Initializing modules..."})
            self._events.emit("cinematic_log", {"text": "Connecting to AI core..."})
            self._events.emit("cinematic_log", {"text": "System ready."})
        except Exception:
            pass

        # Phase 16: Start background vision provider
        self._vision.start()
        logger.info("[VISION] Background vision provider initiated.")

        # Phase 19: Start proactive intelligence loop
        self._start_proactive_loop()

        # Phase 22: Start clipboard monitor
        self._clipboard.start()
        logger.info("[CLIPBOARD] Monitor started.")

        # Phase 28: Start Iron Man Monitor
        if hasattr(self, '_sys_monitor'):
            self._sys_monitor.start()

        # Phase 23: Start File Sorcerer
        self._sorcerer.start()
        logger.info("[SORCERER] Autonomous filing started.")

        # Phase 26: Start Knowledge Indexer
        self._indexer.start()

        # Phase 26: Start Sentinel Fixer
        self._sentinel.start()

        # Phase 24: Habit prediction
        threading.Thread(target=self._predict_needs, daemon=True).start()

        # Phase 26: Log loaded skills
        try:
            from skills import list_skills
            skills = list_skills()
            if skills:
                logger.info("[SKILLS] %d skills loaded: %s", len(skills), [s['name'] for s in skills])
        except Exception:
            pass

        try:
            launch_ui(self._events)
        except Exception as exc:
            logger.error("UI launch failed: %s", exc)
        if audio_thread and audio_thread.is_alive():
            audio_thread.join(timeout=0)
        end_ts = time.monotonic()
        logger.info("Cinematic startup completed in %.2fs", end_ts - start_ts)

    def _predict_needs(self):
        """Predict user needs on startup based on top habits (Phase 24)."""
        habits = self._db.get_top_habits(limit=2)
        if habits:
            msg = "Sir, based on your previous sessions, would you like me to prepare your typical workspace? "
            targets = [h['target'] for h in habits]
            msg += f"I see you often use {', and '.join(targets)}."
            speak(msg)

    # ─── Command Pipeline ────────────────────────────────────

    def _handle_command(self, payload: dict) -> None:
        """
        Master command handler with structured logging (Phase 8).

        Pipeline:
            [INPUT] → [PARSED] → [ACTION] → [EXECUTION] → memory save
        """
        interaction_steps = []
        final_result = None
        interaction_done = False
        start = time.monotonic()

        try:
            raw_text = payload.get("text", "")
            text = raw_text.lower().strip() if raw_text else ""
            self._context.set_intent(raw_text)
            self._context.set_task(True)

            self._interactions.reset()
            if raw_text:
                self._interactions.immediate_ack(raw_text)
                self._interactions.stream_thinking(raw_text)

            # ── [INPUT] ──────────────────────────────────────
            source = payload.get("source", "text")
            logger.info("[INPUT] source=%s text='%s'", source, text)

            # Signal overlay: thinking
            self._events.emit("overlay_state", {"state": "thinking", "text": text[:40]})

            # ── [PARSED] ─────────────────────────────────────
            route_result = route_command(text)
            logger.info("[PARSED] result=%s", _summary(route_result))

            # Agent loop for context-driven follow-ups or unknowns
            if self._should_use_agent_loop(route_result):
                result, interaction_steps = self._run_agent_loop(raw_text)
                final_result = result
                interaction_done = True
                return

            # Multi-step: route_command may return a list
            if isinstance(route_result, list):
                # Phase 5: execute each step sequentially
                result, interaction_steps = self._execute_multi_step(route_result, text, payload)
                final_result = result
                self._interactions.finish(result.get("message", "Sequence completed."))
                interaction_done = True
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
                self._interactions.finish(result.get("message", "Done."))
                interaction_done = True
                return

            # ── Chat (greeting) — speak immediately ──────────
            if action == "chat":
                extra = result.get("extra", {})
                exec_result = execute_action(action, result.get("target", ""))
                result["exec_result"] = exec_result
                result["message"] = exec_result.get("message", "")
                logger.info("[ACTION] chat → '%s'", exec_result.get("message", ""))
                self._context.update_after_action(action, result.get("target", ""), extra, exec_result)
                self._events.emit("command_result", result)
                final_result = result
                self._interactions.finish(result.get("message", "Done."))
                interaction_done = True
                return

            # ── [ACTION] Execute known action ────────────────
            target = result.get("target", "")
            extra = result.get("extra", {})

            if action not in ("noop",):
                self._interactions.narrate_action(action, target)
                logger.info("[ACTION] Executing: %s target='%s'", action, target)
                exec_result = execute_action(action, target, extra)
                result["exec_result"] = exec_result
                result["message"] = exec_result.get("message", result.get("message", ""))
                self._context.update_after_action(action, target, extra, exec_result)

                # Phase 24: Log usage for habits
                if action in ["open_app", "open_url", "trigger_n8n"]:
                    self._db.log_usage(action, target)

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

            final_result = result
            if not interaction_done:
                self._interactions.finish(result.get("message", "Done."))
                interaction_done = True

        except Exception as exc:
            final_result = {"action": "error", "message": str(exc), "type": "error"}
            logger.error("[ERROR] Command handling failed: %s", exc, exc_info=True)
        finally:
            try:
                if not interaction_done and final_result is not None:
                    self._interactions.finish(final_result.get("message", "Done."))
                elif not interaction_done:
                    self._interactions.stop()
            except Exception:
                self._interactions.stop()
            elapsed = time.monotonic() - start
            logger.info("[PERF] Command processed in %.3fs", elapsed)
            try:
                save_interaction(payload.get("text", ""), interaction_steps, final_result or {})
            except Exception as exc:
                logger.error("[ERROR] Memory persistence failed: %s", exc)
            self._context.set_task(False)

            # Phase 27: Learn personality from this interaction
            try:
                user_text = payload.get("text", "")
                ai_msg = (final_result or {}).get("message", "")
                if user_text:
                    learn_from_interaction(user_text, ai_msg)
            except Exception:
                pass

    # ─── Multi-Step Execution (Phase 5) ──────────────────────

    def _execute_multi_step(self, steps: List[dict], text: str, payload: dict) -> tuple[dict, List[dict]]:
        """Execute a list of routed command steps sequentially (Phase 5)."""
        logger.info("[MULTI-STEP] Executing %d steps for text='%s'", len(steps), text)
        all_interaction_steps = []
        previous = None
        final_result = {"type": "multi_step", "steps": []}

        for i, step_result in enumerate(steps):
            action = step_result.get("action", "")
            target = step_result.get("target", "")
            extra = step_result.get("extra", {})

            # ── [PARSED] Step ────────────────────────────────
            logger.info("[PARSED] Step %d/%d: action=%s target='%s'", i + 1, len(steps), action, target)
            try:
                self._events.emit("command_progress", {"stage": f"step_{i+1}", "text": f"{action}: {target}"})
            except Exception:
                pass

            if action == "unknown":
                step_result, ai_steps = self._handle_unknown(text, step_result)
                all_interaction_steps.extend(ai_steps)
            elif action == "chat":
                logger.info("[ACTION] Step %d: chat", i + 1)
                exec_result = execute_action(action, target)
                step_result["exec_result"] = exec_result
                self._context.update_after_action(action, target, extra, exec_result)
                logger.info("[EXECUTION] Step %d: chat completed", i + 1)
            elif action not in ("noop",):
                # ── [ACTION] Execute Step ────────────────────
                logger.info("[ACTION] Step %d: %s target='%s'", i + 1, action, target)
                exec_result = execute_action(action, target, extra, previous_result=previous)
                step_result["exec_result"] = exec_result
                step_result["message"] = exec_result.get("message", step_result.get("message", ""))
                self._context.update_after_action(action, target, extra, exec_result)

                # Phase 24: Log usage for habits (multi-step)
                if action in ["open_app", "open_url", "trigger_n8n"]:
                    self._db.log_usage(action, target)

                # ── [EXECUTION] Log Step ─────────────────────
                logger.info("[EXECUTION] Step %d: status=%s message='%s'",
                            i + 1, exec_result.get("status"), exec_result.get("message", ""))

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

        last_msg = final_result["steps"][-1].get("message", "") if final_result["steps"] else ""
        final_result["message"] = last_msg or "Sequence completed."

        return final_result, all_interaction_steps

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

            ai_msg = ai_result.get("message")

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

                result = {"steps": step_results, "type": "ai", "message": ai_msg}
            else:
                result = {"action": "unknown", "target": "", "message": ai_msg or "I'm not sure how to handle that.", "type": "ai"}
        except Exception as exc:
            logger.error("[AI-FALLBACK] AI interpretation failed: %s", exc)
            result = {"action": "error", "message": f"Sir, my AI systems encountered an error: {exc}", "type": "error"}

        return result, interaction_steps

    # ─── Step Execution ──────────────────────────────────────

    def _execute_step(self, step: dict, previous_result: Optional[dict] = None) -> dict:
        action = step.get("action", "")
        target = step.get("target", "") or (previous_result or {}).get("output", "")
        extra = step.get("extra", {})
        if not action:
            return {"success": False, "status": "error", "message": "Missing action"}
        result = execute_action(action, target, extra, previous_result=previous_result)
        self._context.update_after_action(action, target, extra, result)
        return result

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
            
            # Phase 26: Support skill prefix and check against registry
            if not action.startswith("skill:") and action not in ACTION_REGISTRY and action != "open_dynamic":
                return {"error": f"Unsupported action: {action}"}
            key = (action, target, json.dumps(extra, sort_keys=True, default=str))
            if key in seen:
                continue
            seen.add(key)
            deduped.append({"action": action, "target": target, "extra": extra})
        if not deduped:
            return {"error": "No valid steps"}
        return {"steps": deduped}

    # ─── Agent Loop (Context-Aware) ──────────────────────────

    def _should_use_agent_loop(self, route_result) -> bool:
        """Decide whether to invoke the planner-based agent loop."""
        if isinstance(route_result, list):
            return False
        action = route_result.get("action") if isinstance(route_result, dict) else "unknown"
        if action == "unknown":
            return True
        if self._context.has_active_context() and action in ("chat", "media_control", "noop", "quick_search"):
            return True
        if self._context.task_in_progress and action not in ("open_app", "open_dynamic", "open_url", "open_folder", "power_state", "system_check"):
            return True
        return False

    def _run_agent_loop(self, command: str) -> tuple[dict, list]:
        """Plan → act → observe loop using the tool abstraction layer."""
        try:
            visual = ""
            try:
                from brain.vision_provider import get_visual_context
                visual = get_visual_context()
            except Exception:
                visual = ""
            executed_steps = []
            pending_steps: List[dict] = []
            planner_msg = ""
            feedback = ""
            max_steps = 3
            last_tool = None
            last_input = None

            for _ in range(max_steps):
                if not pending_steps:
                    ctx_snapshot = self._context.snapshot()
                    steps, planner_msg = plan_steps(command, ctx_snapshot, visual, feedback=feedback)
                    feedback = ""
                    pending_steps = steps or []
                    if not pending_steps:
                        final_message = planner_msg or feedback or "Task complete."
                        result_payload = {"type": "agent_loop", "steps": executed_steps, "message": final_message}
                        self._events.emit("command_result", result_payload)
                        self._interactions.finish(final_message)
                        return result_payload, executed_steps

                step = pending_steps.pop(0)
                tool = step.get("tool", "")
                reason = step.get("reason", "")
                if reason:
                    self._events.emit("command_progress", {"stage": "agent", "text": reason})
                self._announce_agent_step(tool, step.get("input", ""))
                input_arg = step.get("input", "")

                if last_tool and tool == last_tool and input_arg == (last_input or ""):
                    final_message = planner_msg or f"Stopping: repeated action {tool}."
                    result_payload = {"type": "agent_loop", "steps": executed_steps, "message": final_message}
                    self._events.emit("command_result", result_payload)
                    self._interactions.finish(final_message)
                    return result_payload, executed_steps

                before_ctx = self._context.snapshot()
                result = self._execute_tool_step(tool, input_arg)
                self._context.update_after_action(tool, input_arg, {}, result)
                after_ctx = self._context.snapshot()
                executed_steps.append({"step": step, "result": result})

                status_line = result.get("message") or result.get("status") or ""
                if status_line:
                    self._events.emit("command_progress", {"stage": "agent_step", "text": status_line})

                pending_steps.clear()

                if not self._has_progress(before_ctx, after_ctx, result):
                    final_message = planner_msg or "Stopping: no progress detected."
                    result_payload = {"type": "agent_loop", "steps": executed_steps, "message": final_message}
                    self._events.emit("command_result", result_payload)
                    self._interactions.finish(final_message)
                    return result_payload, executed_steps

                last_tool = tool
                last_input = input_arg

                if not result.get("success", True):
                    feedback = f"Step {tool} failed: {status_line or 'no message'}. Continue from current app/url."
                    continue

            final_message = planner_msg or (executed_steps[-1]["result"].get("message", "") if executed_steps else "Reached agent limit.")
            if executed_steps and executed_steps[-1]["result"].get("success") is False:
                final_message = f"{final_message} Need guidance for the next move."
            if len(executed_steps) >= max_steps and not planner_msg:
                final_message = f"{final_message} (stopped after {max_steps} steps)"
            result_payload = {"type": "agent_loop", "steps": executed_steps, "message": final_message}
            self._events.emit("command_result", result_payload)
            self._interactions.finish(final_message)
            return result_payload, executed_steps
        except Exception as exc:
            logger.error("[AGENT] Agent loop failed: %s", exc, exc_info=True)
            result_payload = {"type": "agent_loop", "message": f"Agent loop error: {exc}"}
            self._events.emit("command_result", result_payload)
            self._interactions.finish(result_payload["message"])
            return result_payload, []

    def _execute_tool_step(self, tool: str, arg: str) -> dict:
        tool = tool or ""
        if tool == "open_app":
            return agent_tools.open_app(arg)
        if tool == "type_text":
            return agent_tools.type_text(arg)
        if tool == "press_key":
            return agent_tools.press_key(arg)
        if tool == "click":
            return agent_tools.click(arg)
        if tool == "read_screen":
            return agent_tools.read_screen()
        if tool == "get_active_app":
            return agent_tools.get_active_app()
        if tool == "open_url":
            return execute_action("open_dynamic", arg, {"resolved_type": "url"})
        return {"success": False, "status": "error", "message": f"Unknown tool {tool}"}

    def _announce_agent_step(self, tool: str, arg: str) -> None:
        desc = arg if arg else tool
        try:
            self._events.emit("overlay_state", {"state": "acting", "text": desc[:60]})
        except Exception:
            pass
        self._interactions.narrate_action(tool, arg)

    @staticmethod
    def _has_progress(before: dict, after: dict, result: dict) -> bool:
        """Detect whether context or output moved forward to prevent loops."""
        keys = ("current_app", "current_url", "last_action", "last_result_status", "last_result_message", "task_in_progress")
        for key in keys:
            if before.get(key) != after.get(key):
                return True
        if result.get("success") and result.get("output"):
            return True
        return False

    # ─── Proactive Intelligence (Phase 19) ────────────────────

    def _start_proactive_loop(self) -> None:
        """Start the background proactivity loop using ProactiveEngine."""
        get_proactive_engine(self._events).start()


    # ─── Shutdown ────────────────────────────────────────────

    def _shutdown(self) -> None:
        self._running = False
        # Stop File Sorcerer (Phase 23)
        try:
            self._sorcerer.stop()
        except Exception as exc:
            logger.error("Error stopping file sorcerer: %s", exc)

        # Log cache stats on shutdown
        stats = route_cache.stats
        logger.info("[PERF] Cache stats: %s", stats)

        # Stop proactive loop
        try:
            get_proactive_engine().stop()
        except Exception as exc:
            logger.error("Error stopping proactive engine: %s", exc)

        # Stop Knowledge Indexer
        try:
            self._indexer.stop()
        except Exception:
            pass

        # Stop vision provider
        try:
            self._vision.stop()
        except Exception as exc:
            logger.error("Error stopping vision provider: %s", exc)

        # Stop Iron Man System Monitor
        try:
            if hasattr(self, '_sys_monitor'):
                self._sys_monitor.stop()
        except Exception as exc:
            logger.error("Error stopping system monitor: %s", exc)

        # Stop clipboard monitor (Phase 22)
        try:
            self._clipboard.stop()
        except Exception as exc:
            logger.error("Error stopping clipboard monitor: %s", exc)

        # Stop wake word detector (Phase 20)
        try:
            self._wake_word.stop()
        except Exception as exc:
            logger.error("Error stopping wake word: %s", exc)

        try:
            self._clap_detector.stop()
        except Exception as exc:
            logger.error("Error stopping clap detector: %s", exc)

        # Stop MCP Hub
        try:
            if hasattr(self, '_mcp_hub'):
                self._mcp_hub.stop()
        except Exception as exc:
            logger.error("Error stopping MCP hub: %s", exc)

        # Stop Sentinel Fixer
        try:
            self._sentinel.stop()
        except Exception:
            pass

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
