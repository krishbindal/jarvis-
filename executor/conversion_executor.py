from __future__ import annotations

"""Conversion executor using ffmpeg and Pillow."""

import subprocess
from pathlib import Path
from typing import Dict

from PIL import Image


def _resolve(path: str) -> Path:
    target = Path(path).expanduser().resolve()
    return target


def convert_to_mp3(file_path: str) -> Dict:
    try:
        source = _resolve(file_path)
        if not source.exists():
            return {"success": False, "status": "error", "message": f"File not found: {source}"}
        dest = source.with_suffix(".mp3")
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(source),
            "-vn",
            "-acodec",
            "libmp3lame",
            str(dest),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            return {"success": False, "status": "error", "message": f"ffmpeg failed: {result.stderr.strip()}"}
        return {"success": True, "status": "success", "message": f"Converted to MP3: {dest}", "path": str(dest), "output": str(dest)}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "status": "error", "message": f"Conversion failed: {exc}"}


def convert_to_pdf(file_path: str) -> Dict:
    try:
        source = _resolve(file_path)
        if not source.exists():
            return {"success": False, "status": "error", "message": f"File not found: {source}"}
        dest = source.with_suffix(".pdf")
        with Image.open(source) as img:
            rgb = img.convert("RGB")
            rgb.save(dest, "PDF", resolution=100.0)
        return {"success": True, "status": "success", "message": f"Converted to PDF: {dest}", "path": str(dest), "output": str(dest)}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "status": "error", "message": f"Conversion failed: {exc}"}


def execute_conversion(action: str, target: str) -> Dict:
    if action == "convert_to_mp3":
        return convert_to_mp3(target)
    if action == "convert_to_pdf":
        return convert_to_pdf(target)
    return {"success": False, "message": f"Unsupported conversion: {action}"}
