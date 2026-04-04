from __future__ import annotations

"""Central registry for executable actions."""

from typing import Any, Dict, Optional

from executor.conversion_executor import convert_to_mp3, convert_to_pdf
from executor.download_executor import download_file, download_video
from executor.n8n_executor import trigger_workflow
from executor.system_executor import (
    copy_file,
    create_folder,
    delete_file,
    file_info,
    list_files,
    move_file,
    rename_file,
    search_file,
    open_app,
    media_control,
    power_state,
    capture_screen,
    quick_search,
    open_url,
)

ACTION_REGISTRY = {
    "list_files": list_files,
    "create_folder": create_folder,
    "delete_file": delete_file,
    "move_file": move_file,
    "copy_file": copy_file,
    "rename_file": rename_file,
    "search_file": search_file,
    "file_info": file_info,
    "download_file": download_file,
    "download_video": download_video,
    "convert_to_mp3": convert_to_mp3,
    "convert_to_pdf": convert_to_pdf,
    "trigger_n8n": trigger_workflow,
    "open_app": open_app,
    "media_control": media_control,
    "power_state": power_state,
    "capture_screen": capture_screen,
    "quick_search": quick_search,
    "open_url": open_url,
}


def execute_action(
    action: str,
    target: str = "",
    extra: Optional[Dict[str, Any]] = None,
    previous_result: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    func = ACTION_REGISTRY.get(action)
    if not func:
        return {"success": False, "status": "error", "message": f"Unsupported action: {action}"}

    extra = extra or {}

    if action == "create_folder":
        return func(target, extra.get("path"))
    if action in ("move_file", "copy_file"):
        return func(extra.get("source", ""), target)
    if action == "rename_file":
        return func(target, extra.get("new_name", ""))
    if action == "search_file":
        return func(target, extra.get("root_path", ""))
    if action == "trigger_n8n":
        data = dict(extra)
        if previous_result and "previous_output" not in data:
            data["previous_output"] = previous_result.get("output", previous_result)
        return func(target or action, data)
    return func(target)
