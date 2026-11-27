"""Safe, bounded media conversions that never overwrite existing files."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
from typing import Dict

from PIL import Image

from utils.logger import get_logger

logger = get_logger(__name__)
_TIMEOUT_SECONDS = 120
_MAX_COLLISIONS = 1000


def _resolve(path: str) -> Path:
    if not isinstance(path, str) or not path.strip():
        raise ValueError("A nonempty file path is required.")
    return Path(path).expanduser().resolve()


def _unique_completed_file(temporary_output: Path, desired: Path) -> Path:
    """Hard-link a finished file without overwriting, on the same filesystem."""
    if not temporary_output.is_file() or temporary_output.stat().st_size == 0:
        raise ValueError("Converter returned without a nonempty output file.")
    for number in range(_MAX_COLLISIONS):
        destination = desired if number == 0 else desired.with_name(f"{desired.stem} ({number}){desired.suffix}")
        try:
            # os.link fails with FileExistsError atomically if a destination was
            # created after an earlier check. Never use ffmpeg -y or replace().
            os.link(temporary_output, destination)
            return destination
        except FileExistsError:
            continue
    raise FileExistsError("No available output filename after 1000 attempts.")


def convert_to_mp3(file_path: str) -> Dict:
    try:
        source = _resolve(file_path)
        if not source.is_file():
            return {"success": False, "status": "not_found", "message": "Source is not an existing file."}
        with tempfile.TemporaryDirectory(prefix=".jarvis-convert-", dir=source.parent) as temp:
            output = Path(temp) / "converted.mp3"
            command = [
                "ffmpeg", "-hide_banner", "-nostdin", "-n",
                "-i", str(source), "-vn", "-acodec", "libmp3lame", str(output),
            ]
            result = subprocess.run(
                command, capture_output=True, text=True, check=False, timeout=_TIMEOUT_SECONDS,
            )
            if result.returncode != 0:
                logger.warning("[CONVERSION] ffmpeg rejected file (%s)", result.returncode)
                return {
                    "success": False, "status": "conversion_failed",
                    "message": "FFmpeg failed; the source was not modified.",
                }
            try:
                dest = _unique_completed_file(output, source.with_suffix(".mp3"))
            except ValueError:
                return {
                    "success": False, "status": "output_unverified",
                    "message": "FFmpeg returned success but produced no nonempty MP3.",
                }
        return {
            "success": True, "status": "file_created",
            "message": f"Nonempty MP3 was created at {dest}; audio fidelity was not tested.",
            "path": str(dest), "output": str(dest),
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False, "status": "timeout",
            "message": "FFmpeg exceeded the 120-second timeout. No final output was published.",
        }
    except (OSError, ValueError, FileExistsError) as exc:
        logger.warning("[CONVERSION] MP3 conversion failed (%s)", type(exc).__name__)
        return {"success": False, "status": "error", "message": "MP3 conversion failed without modifying the source."}


def convert_to_pdf(file_path: str) -> Dict:
    try:
        source = _resolve(file_path)
        if not source.is_file():
            return {"success": False, "status": "not_found", "message": "Source is not an existing image file."}
        with tempfile.TemporaryDirectory(prefix=".jarvis-convert-", dir=source.parent) as temp:
            output = Path(temp) / "converted.pdf"
            with Image.open(source) as image:
                rgb = image.convert("RGB")
                try:
                    rgb.save(output, "PDF", resolution=100.0)
                finally:
                    rgb.close()
            if not output.is_file() or output.stat().st_size < 5:
                return {
                    "success": False, "status": "output_unverified",
                    "message": "PDF conversion produced no usable output file.",
                }
            with output.open("rb") as stream:
                signature = stream.read(5)
            if signature != b"%PDF-":
                return {
                    "success": False, "status": "output_unverified",
                    "message": "PDF output header was invalid; no final output was published.",
                }
            dest = _unique_completed_file(output, source.with_suffix(".pdf"))
        return {
            "success": True, "status": "file_created",
            "message": f"PDF file created at {dest}; document rendering was not independently checked.",
            "path": str(dest), "output": str(dest),
        }
    except (OSError, ValueError, FileExistsError) as exc:
        logger.warning("[CONVERSION] PDF conversion failed (%s)", type(exc).__name__)
        return {"success": False, "status": "error", "message": "PDF conversion failed without changing the source."}


def execute_conversion(action: str, target: str) -> Dict:
    if action == "convert_to_mp3":
        return convert_to_mp3(target)
    if action == "convert_to_pdf":
        return convert_to_pdf(target)
    return {"success": False, "status": "unsupported", "message": f"Unsupported conversion: {action}"}
