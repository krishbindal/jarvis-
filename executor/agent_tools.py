from __future__ import annotations

"""Lightweight tool abstractions for the agent planner."""

import time
from typing import Dict, Any

import pyautogui

from executor.system_executor import open_app as system_open_app, capture_screen
from utils.system_context import get_active_process_name, get_active_window_title


def open_app(name: str) -> Dict[str, Any]:
    return system_open_app(name)


def type_text(text: str) -> Dict[str, Any]:
    try:
        pyautogui.typewrite(text, interval=0.02)
        return {"success": True, "status": "success", "message": f"Typed '{text}'"}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "status": "error", "message": str(exc)}


def press_key(key: str) -> Dict[str, Any]:
    try:
        if "+" in key:
            parts = key.split("+")
            pyautogui.hotkey(*[p.strip() for p in parts if p.strip()])
        else:
            pyautogui.press(key.strip())
        return {"success": True, "status": "success", "message": f"Pressed {key}"}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "status": "error", "message": str(exc)}


def click(description: str = "") -> Dict[str, Any]:
    """Simple click at current cursor position; description is for logging."""
    try:
        pyautogui.click()
        return {"success": True, "status": "success", "message": f"Clicked {description}".strip()}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "status": "error", "message": str(exc)}


def read_screen() -> Dict[str, Any]:
    """Capture the current screen and return path + active app hints."""
    shot = capture_screen()
    shot["active_window"] = get_active_window_title()
    shot["active_process"] = get_active_process_name()
    return shot


def get_active_app() -> Dict[str, Any]:
    return {
        "success": True,
        "status": "success",
        "message": "Active app captured.",
        "output": {
            "window": get_active_window_title(),
            "process": get_active_process_name(),
        },
    }
