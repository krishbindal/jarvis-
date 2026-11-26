"""Evidence-first result contracts.

An AI plan, narration or missing status field must never be treated as proof
that a tool succeeded. Tool-reported success is still not independent OS-level
verification; callers must describe it accurately.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable


_ERROR_STATUSES = {"error", "failed", "failure", "disabled", "denied", "approval_required", "cancelled", "timeout", "partial"}


def normalize_executor_result(value: Any, action: str = "action") -> Dict[str, Any]:
    """Return a predictable result, failing closed for malformed tool responses."""
    if not isinstance(value, dict):
        return {
            "success": False,
            "status": "invalid_result",
            "message": f"{action} returned no structured execution result.",
        }
    response = dict(value)
    status = response.get("status")
    status_name = status.strip().lower() if isinstance(status, str) else ""
    explicit = response.get("success")
    if not isinstance(explicit, bool):
        return {
            "success": False,
            "status": "unverified",
            "message": f"{action} returned no explicit success confirmation.",
        }
    if explicit and status_name in _ERROR_STATUSES:
        return {
            "success": False,
            "status": "inconsistent_result",
            "message": f"{action} reported conflicting execution status.",
        }
    response["success"] = explicit
    if not status_name:
        response["status"] = "success" if explicit else "error"
    if not isinstance(response.get("message"), str):
        response["message"] = (
            f"{action} reported success; external state was not checked."
            if explicit else f"{action} failed without an explanation."
        )
    return response


def summarize_execution_results(
    results: Iterable[Any],
    expected: int | None = None,
) -> Dict[str, Any]:
    """Summarize observed executor results, never a planner's proposed narrative."""
    collected = [
        normalize_executor_result(value, action=f"Step {i}")
        for i, value in enumerate(results, 1)
    ]
    count = len(collected)
    total = max(count, expected) if isinstance(expected, int) and expected >= 0 else count
    passed = sum(item["success"] is True for item in collected)

    if not count:
        return {
            "success": False,
            "status": "not_executed",
            "message": "No tool action ran. I cannot confirm that the task was completed.",
            "reported_successes": 0,
            "attempted_steps": 0,
        }

    if passed == count and count == total:
        return {
            "success": True,
            "status": "success",
            "message": (
                f"Executors reported success for {passed}/{total} steps. "
                "External results have not been independently checked."
            ),
            "reported_successes": passed,
            "attempted_steps": count,
        }

    first_failure = next(
        (item for item in collected if item["success"] is not True), None
    )
    detail = (first_failure or {}).get("message") or "The requested result was not confirmed."
    # Avoid presenting unbounded or private tool output as a status line.
    detail = " ".join(str(detail).split())[:180]
    return {
        "success": False,
        "status": "partial" if passed else "failed",
        "message": (
            f"Executor results: {passed}/{total} steps reported success. "
            f"Stopped or unverified: {detail}"
        ),
        "reported_successes": passed,
        "attempted_steps": count,
    }
