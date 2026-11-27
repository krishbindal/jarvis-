"""Music playback with observable outcomes and non-overwriting downloads.

Audio is handled inside the existing command worker: success is not returned
before yt-dlp completes. No claim is made that the user actually heard music.
"""
from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys
import threading
from typing import Any, Dict
from uuid import uuid4

from utils.logger import get_logger

logger = get_logger(__name__)

SKILL_NAME = "music"
SKILL_DESCRIPTION = "Download or request playback of YouTube audio with truthful statuses"
SKILL_PATTERNS = [
    r"play\s+(?:some\s+)?(?:music|song|songs|beats|track)\s*(.*)$",
    r"play\s+(.+?)(?:\s+on\s+youtube)?$",
    r"stop\s+(?:the\s+)?music",
    r"pause\s+(?:the\s+)?music",
    r"download\s+(?:the\s+)?(?:music|song|audio)\s*(.*)$",
]

_MUSIC_DIR = Path.home() / "Music" / "jarvis_cache"
_PLAY_LOCK = threading.Lock()
_MAX_QUERY_LENGTH = 200


def _download_audio(query: str, destination: Path) -> Dict[str, Any]:
    """Run yt-dlp synchronously and require the actual expected nonempty file."""
    if not isinstance(query, str) or not query.strip() or len(query) > _MAX_QUERY_LENGTH:
        return {"success": False, "status": "invalid_query", "message": "Music query must be 1–200 characters."}
    try:
        destination = Path(destination)
        destination.mkdir(parents=True, exist_ok=True)
        token = "jarvis_audio_" + uuid4().hex
        template = destination / (token + ".%(ext)s")
        command = [
            sys.executable, "-m", "yt_dlp",
            f"ytsearch1:{query}", "--extract-audio", "--audio-format", "mp3",
            "--audio-quality", "5", "-o", str(template),
            "--no-playlist", "--no-overwrites", "--quiet",
        ]
        result = subprocess.run(command, timeout=90, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            return {
                "success": False,
                "status": "download_failed",
                "message": "yt-dlp failed to produce the requested audio. Check local logs and ffmpeg availability.",
            }
        audio_file = destination / (token + ".mp3")
        if not audio_file.is_file() or audio_file.stat().st_size <= 0:
            return {
                "success": False,
                "status": "missing_output",
                "message": "yt-dlp returned, but no nonempty MP3 file was observed.",
            }
        return {"success": True, "status": "download_verified", "path": str(audio_file)}
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        logger.warning("[MUSIC] Audio conversion failed (%s)", type(exc).__name__)
        return {"success": False, "status": "download_error", "message": "Audio could not be downloaded or converted."}


def _clean_query(target: str) -> str:
    query = target.strip()
    query = re.sub(
        r"^(?:download|play)(?:\s+(?:some|the|music|song|songs|audio))?\s*",
        "", query, flags=re.IGNORECASE,
    ).strip()
    query = re.sub(r"\s+on\s+youtube\s*$", "", query, flags=re.IGNORECASE).strip()
    return query or "lofi hip hop beats"


def execute(target: str, extra: Dict[str, Any] = None) -> Dict[str, Any]:
    """Only acknowledge playback after download and mixer have actually run."""
    if not isinstance(target, str) or not target.strip():
        return {"success": False, "status": "invalid_request", "message": "A music command is required."}
    lower = target.lower().strip()
    if lower.startswith(("stop", "pause")):
        try:
            import pygame
            if not pygame.mixer.get_init() or not pygame.mixer.music.get_busy():
                return {"success": False, "status": "not_playing", "message": "No active audio playback was observed."}
            if lower.startswith("pause"):
                pygame.mixer.music.pause()
                return {
                    "success": True,
                    "status": "pause_requested",
                    "message": "Pause command issued to the mixer; audible output was not independently checked.",
                }
            pygame.mixer.music.stop()
            return {"success": True, "status": "stop_requested", "message": "Stop command issued to the audio mixer."}
        except (ImportError, OSError, RuntimeError) as exc:
            logger.warning("[MUSIC] Mixer command failed (%s)", type(exc).__name__)
            return {"success": False, "status": "mixer_error", "message": "Music mixer command failed."}

    if not _PLAY_LOCK.acquire(blocking=False):
        return {"success": False, "status": "busy", "message": "Another audio operation is currently running."}
    try:
        query = _clean_query(target)
        if len(query) > _MAX_QUERY_LENGTH:
            return {"success": False, "status": "invalid_query", "message": "Music query exceeds 200 characters."}
        is_download = lower.startswith("download")
        if is_download:
            from config import DOWNLOAD_DIR
            directory = Path(DOWNLOAD_DIR).expanduser()
        else:
            directory = _MUSIC_DIR
        result = _download_audio(query, directory)
        if result.get("success") is not True:
            return result
        filepath = Path(result["path"])
        if is_download:
            return {
                "success": True,
                "status": "file_observed",
                "message": f"Downloaded audio file verified at {filepath}. File playback was not tested.",
                "path": str(filepath),
                "output": str(filepath),
            }
        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.music.load(str(filepath))
            pygame.mixer.music.play()
            if not pygame.mixer.music.get_busy():
                return {
                    "success": False,
                    "status": "playback_unverified",
                    "message": "Mixer did not report active playback after play was requested.",
                }
            return {
                "success": True,
                "status": "mixer_playback_observed",
                "message": f"Mixer reports audio playback started for '{query}'. Audible speaker output was not verified.",
                "path": str(filepath),
                "output": str(filepath),
            }
        except (ImportError, OSError, RuntimeError) as exc:
            logger.warning("[MUSIC] Playback failed (%s)", type(exc).__name__)
            return {
                "success": False,
                "status": "playback_failed",
                "message": "Audio downloaded but could not be started through the mixer.",
                "path": str(filepath),
            }
    finally:
        _PLAY_LOCK.release()
