from __future__ import annotations

"""Lightweight tool abstractions for the agent planner."""

import time
from typing import Dict, Any

try:
    import pyautogui
    _PYAUTOGUI_ERROR = None
except Exception as exc:  # noqa: BLE001
    pyautogui = None
    _PYAUTOGUI_ERROR = exc

from executor.system_executor import open_app as system_open_app, capture_screen
from utils.system_context import get_active_process_name, get_active_window_title


def open_app(name: str) -> Dict[str, Any]:
    return system_open_app(name)


def type_text(text: str) -> Dict[str, Any]:
    try:
        if not pyautogui:
            return {"success": False, "status": "error", "message": f"pyautogui unavailable: {_PYAUTOGUI_ERROR}"}
        pyautogui.typewrite(text, interval=0.02)
        return {"success": True, "status": "success", "message": f"Typed '{text}'"}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "status": "error", "message": str(exc)}


def press_key(key: str) -> Dict[str, Any]:
    try:
        if not pyautogui:
            return {"success": False, "status": "error", "message": f"pyautogui unavailable: {_PYAUTOGUI_ERROR}"}
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
        if not pyautogui:
            return {"success": False, "status": "error", "message": f"pyautogui unavailable: {_PYAUTOGUI_ERROR}"}
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


def scroll(amount: int | str = -800) -> Dict[str, Any]:
    """Scroll the screen by the requested amount."""
    try:
        distance = int(amount)
    except Exception:
        distance = -800
    try:
        if not pyautogui:
            return {"success": False, "status": "error", "message": f"pyautogui unavailable: {_PYAUTOGUI_ERROR}"}
        pyautogui.scroll(distance)
        return {"success": True, "status": "success", "message": f"Scrolled {distance}"}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "status": "error", "message": str(exc)}


# ── Python Code Interpreter (Phase 35) ───────────────────────

def execute_python(code: str) -> Dict[str, Any]:
    """Execute opted-in Python with a filtered environment; NOT a sandbox."""
    from executor.python_runner import run_python_code
    return run_python_code(code)


# ── Semantic UI Automation (Phase 35) ─────────────────────────

def get_ui_tree(depth: int = 3) -> Dict[str, Any]:
    """Read the Windows Accessibility tree of the active window."""
    try:
        import uiautomation as auto

        root = auto.GetForegroundControl()
        if not root:
            return {"success": False, "status": "error", "message": "No foreground window found."}

        def _walk(ctrl, d: int = 0) -> list:
            items = []
            if d > depth:
                return items
            try:
                name = ctrl.Name or ""
                ctrl_type = ctrl.ControlTypeName or ""
                auto_id = ctrl.AutomationId or ""
                entry = {"type": ctrl_type, "name": name}
                if auto_id:
                    entry["id"] = auto_id
                items.append(entry)
                for child in ctrl.GetChildren():
                    items.extend(_walk(child, d + 1))
            except Exception:
                pass
            return items

        tree = _walk(root)
        # Truncate to avoid massive payloads
        tree = tree[:80]
        summary = ", ".join([f"{e['type']}:{e['name'][:30]}" for e in tree[:20] if e.get('name')])

        return {
            "success": True,
            "status": "success",
            "message": f"UI tree: {summary[:200]}",
            "output": tree,
        }
    except ImportError:
        return {"success": False, "status": "error", "message": "uiautomation library not installed. Run: pip install uiautomation"}
    except Exception as exc:
        return {"success": False, "status": "error", "message": f"UI tree read failed: {exc}"}


def click_element(name: str) -> Dict[str, Any]:
    """Click a native Windows UI element by its Name or AutomationId."""
    try:
        import uiautomation as auto

        root = auto.GetForegroundControl()
        if not root:
            return {"success": False, "status": "error", "message": "No foreground window."}

        # Search by Name first, then by AutomationId
        target = root.GetFirstChildControl(auto.NameCondition(name))
        if not target:
            target = root.GetFirstChildControl(auto.AutomationIdCondition(name))

        if target:
            try:
                pattern = target.GetInvokePattern()
                if pattern:
                    pattern.Invoke()
                    return {"success": True, "status": "success", "message": f"Clicked element '{name}' via Invoke."}
            except Exception:
                pass
            # Fallback: click at center of the element
            rect = target.BoundingRectangle
            if rect:
                cx = (rect.left + rect.right) // 2
                cy = (rect.top + rect.bottom) // 2
                if pyautogui:
                    pyautogui.click(cx, cy)
                    return {"success": True, "status": "success", "message": f"Clicked '{name}' at ({cx},{cy})."}
            return {"success": False, "status": "error", "message": f"Found '{name}' but could not click it."}
        return {"success": False, "status": "error", "message": f"Element '{name}' not found in the active window."}
    except ImportError:
        return {"success": False, "status": "error", "message": "uiautomation library not installed. Run: pip install uiautomation"}
    except Exception as exc:
        return {"success": False, "status": "error", "message": f"click_element failed: {exc}"}
