"""Deterministic command-router checks. This is NOT an end-to-end stress test.

Never claim external apps, messages, browser actions, or file operations have
succeeded merely because a command mapped to an action name.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

from core.command_router import route_command

TEST_CASES = [
    # Phase 1: Multi-Step
    "open chrome and search best laptops under 1 lakh and then open first result",
    "open youtube and search lo-fi music and then play first video",
    "open google and search python tutorial and then scroll down",
    
    # Phase 2: Cross-App
    "open chrome and search instagram and then open it and then scroll for 5 seconds",
    "open whatsapp and send hi to Krish and then open instagram",
    "open chrome and search weather and extract temperature",
    
    # Phase 3: Context
    "open chrome",
    "search youtube",
    "open youtube and play a video",
    "pause it",
    
    # Phase 4: File System
    "open downloads folder and sort files by date",
    "create a folder named test123 in desktop and open it",
    "search for a pdf file in downloads and open it",
    
    # Phase 5: Download
    "download a youtube video and convert it to mp3",
    "search wallpaper and download first image",
    
    # Phase 6: NLU
    "i want to listen to music, do something",
    "i am bored, open something interesting",
    "talk to Krish and say i will call later",
    
    # Phase 7: Chained
    "open chrome and search python tutorial and open first video and play it",
    "open google and search best phones and open 2 results and compare them",
    
    # Phase 8: Error
    "open something that doesn't exist",
    "send message to unknown person"
]


def run_routing_check(output_path: Path | None = None) -> dict:
    """Measure only route recognition, with explicit no-execution provenance."""
    cases = []
    for index, command in enumerate(TEST_CASES, start=1):
        started = perf_counter()
        try:
            routed = route_command(command)
            steps = routed if isinstance(routed, list) else [routed]
            actions = [
                str(step.get("action", "unknown")) if isinstance(step, dict) else "unknown"
                for step in steps
            ]
            recognized = bool(actions) and all(
                action not in {"unknown", "noop", ""} for action in actions
            )
            result = {
                "id": index,
                "command": command,
                "route_status": "ROUTED" if recognized else "UNROUTABLE",
                "actions": actions,
                "execution_attempted": False,
                "elapsed_ms": round((perf_counter() - started) * 1000, 3),
            }
        except Exception as exc:
            result = {
                "id": index,
                "command": command,
                "route_status": "ROUTER_EXCEPTION",
                "actions": [],
                "execution_attempted": False,
                "error_type": type(exc).__name__,
                "elapsed_ms": round((perf_counter() - started) * 1000, 3),
            }
        cases.append(result)

    report = {
        "kind": "routing_only",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "execution_attempted": False,
        "hardware_validation": False,
        "description": "Action names were parsed but no OS actions or external tasks ran.",
        "results": cases,
        "summary": {
            "total_cases": len(cases),
            "routed_cases": sum(x["route_status"] == "ROUTED" for x in cases),
            "unroutable_cases": sum(x["route_status"] == "UNROUTABLE" for x in cases),
            "router_exceptions": sum(x["route_status"] == "ROUTER_EXCEPTION" for x in cases),
            "verified_completed_tasks": 0,
        },
    }
    destination = Path(output_path) if output_path is not None else Path("artifacts/routing_check.json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        f"Router-only checks: {report['summary']['routed_cases']}/{len(cases)} recognized. "
        "NO external tasks were executed or verified."
    )
    return report


def run_stress_test() -> dict:
    """Legacy entry point: run ROUTING checks only (not execution stress tests)."""
    return run_routing_check()


if __name__ == "__main__":
    run_routing_check()
