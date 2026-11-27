from __future__ import annotations

"""Generic execution engine for automation plans."""

import urllib.parse
from typing import Any, Dict, List, Optional

try:
    import pyautogui
    _PYAUTOGUI_ERROR = None
except Exception as exc:  # noqa: BLE001
    pyautogui = None
    _PYAUTOGUI_ERROR = exc

from automation.plan import AutomationPlan, AutomationStep
from executor import agent_tools
from executor.download_executor import download_file, download_video
from utils.logger import get_logger
from core.action_registry import execute_action
from core.execution_evidence import normalize_executor_result, summarize_execution_results
from core.action_policy import check_action

logger = get_logger(__name__)

BROWSER_APPS = {"chrome", "edge", "msedge", "firefox", "brave", "opera"}


def _safe_emit(events, name: str, payload: Dict[str, Any]) -> None:
    try:
        if events:
            events.emit(name, payload)
    except Exception:
        pass


def _announce(interactions, action: str, target: str) -> None:
    try:
        if interactions:
            interactions.narrate_action(action, target)
    except Exception:
        pass


def _search_url(query: str) -> str:
    return f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"


def _scroll(amount: int) -> Dict[str, Any]:
    if not pyautogui:
        return {"success": False, "status": "error", "message": f"pyautogui unavailable: {_PYAUTOGUI_ERROR}"}
    try:
        pyautogui.scroll(amount)
        return {"success": True, "status": "success", "message": f"Scrolled {amount}"}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "status": "error", "message": str(exc)}


def _execute_step(step: AutomationStep, context_state=None) -> Dict[str, Any]:
    action = step.action
    target = step.target
    app = step.app

    if action == "open_app":
        res = agent_tools.open_app(app or target)
        res["app_used"] = app or target
        return res

    if action in ("open_url", "search"):
        resolved = target if action == "open_url" else _search_url(target)
        extra = {"resolved_type": "url"}
        app_choice = app or (context_state.current_app if context_state and context_state.current_app in BROWSER_APPS else "")
        if app_choice:
            extra["app"] = app_choice
        res = execute_action("open_dynamic", resolved, extra)
        res["resolved_target"] = resolved
        res["app_used"] = app_choice
        return res

    if action in ("click", "type", "download"):
        denied = check_action("automation:" + action, target or step.reason)
        if denied is not None:
            return denied

    if action == "click":
        return agent_tools.click(step.reason or target)

    if action == "type":
        return agent_tools.type_text(target)

    if action == "scroll":
        try:
            amount = int(target) if target else -800
        except ValueError:
            amount = -800
        return _scroll(amount)

    if action == "download":
        url = target
        if "youtube.com" in url or "youtu.be" in url:
            return download_video(url)
        return download_file(url)

    return {"success": False, "status": "error", "message": f"Unsupported action {action}"}


def execute_automation_plan(
    plan: AutomationPlan,
    context_state=None,
    events=None,
    interactions=None,
    cancel_event=None,
) -> Dict[str, Any]:
    """
    Execute an automation plan step-by-step with feedback and context tracking.
    """
    step_results: List[Dict[str, Any]] = []


    _safe_emit(events, "command_progress", {"stage": "plan", "text": plan.goal or "automation"})

    for idx, step in enumerate(plan.steps, start=1):
        if cancel_event is not None and cancel_event.is_set():
            break
        _safe_emit(events, "command_progress", {"stage": f"step_{idx}", "text": f"{step.action}: {step.target}"})
        _announce(interactions, step.action, step.target)

        if cancel_event is not None and cancel_event.is_set():
            break
        try:
            result = normalize_executor_result(_execute_step(step, context_state), step.action)
        except Exception:
            logger.exception("Automation step failed: %s", step.action)
            result = {"success": False, "status": "error",
                      "message": "Automation step raised an exception; its external outcome is unverified."}
        step_result = {
            "action": step.action,
            "target": result.get("resolved_target", step.target),
            "status": result.get("status"),
            "message": result.get("message"),
            "output": result.get("output"),
            "success": result["success"],
        }

        step_results.append(step_result)
        if context_state and result["success"]:
            context_state.update_after_action(
                step.action,
                result.get("resolved_target", step.target),
                {"app": step.app or result.get("app_used"), "resolved_url": result.get("resolved_target")},
                result,
            )

        if not result["success"]:
            break

    observed = summarize_execution_results(step_results, expected=len(plan.steps))
    if cancel_event is not None and cancel_event.is_set() and len(step_results) < len(plan.steps):
        observed.update(success=False, status="cancelled", message="Automation cancelled before remaining steps; completed actions were not undone.")
    return {
        "success": observed["success"],
        "status": observed["status"],
        "message": observed["message"],
        "reported_successes": observed["reported_successes"],
        "attempted_steps": observed["attempted_steps"],
        "steps": step_results,
    }
