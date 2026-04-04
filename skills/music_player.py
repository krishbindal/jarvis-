"""
JARVIS-X Phase 25: Music Control

Skill: Play music from YouTube via yt-dlp + pygame.
Handles: "play lofi beats", "play some music", "stop music"
"""

import os
import subprocess
import threading
from typing import Any, Dict
from utils.logger import get_logger

logger = get_logger(__name__)

SKILL_NAME = "music"
SKILL_DESCRIPTION = "Play music from YouTube — 'play lofi beats', 'stop music'"
SKILL_PATTERNS = [
    r"play\s+(?:some\s+)?(?:music|song|songs|beats|track)\s*(.*)$",
    r"play\s+(.+?)(?:\s+on\s+youtube)?$",
    r"stop\s+(?:the\s+)?music",
    r"pause\s+(?:the\s+)?music",
]

_current_process = None
_music_dir = os.path.join(os.path.expanduser("~"), "Music", "jarvis_cache")


def _ensure_dir():
    os.makedirs(_music_dir, exist_ok=True)


def _search_and_play(query: str):
    """Download audio from YouTube and play via pygame."""
    global _current_process
    import pygame

    _ensure_dir()
    output_path = os.path.join(_music_dir, "now_playing.mp3")

    # Remove old file
    if os.path.exists(output_path):
        try:
            os.remove(output_path)
        except Exception:
            pass

    try:
        # Search and download audio only
        logger.info("[MUSIC] Searching YouTube for: %s", query)
        cmd = [
            "yt-dlp",
            f"ytsearch1:{query}",
            "--extract-audio",
            "--audio-format", "mp3",
            "--audio-quality", "5",
            "-o", output_path,
            "--no-playlist",
            "--quiet",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if not os.path.exists(output_path):
            logger.error("[MUSIC] Download failed: %s", result.stderr[:200])
            return

        # Play with pygame
        if not pygame.mixer.get_init():
            pygame.mixer.init()

        pygame.mixer.music.load(output_path)
        pygame.mixer.music.play()
        logger.info("[MUSIC] Now playing: %s", query)

    except Exception as e:
        logger.error("[MUSIC] Playback failed: %s", e)


def execute(target: str, extra: Dict[str, Any] = None) -> Dict[str, Any]:
    """Handle music commands."""
    import re
    target_lower = target.lower().strip()

    # Stop/Pause
    if any(w in target_lower for w in ["stop", "pause"]):
        try:
            import pygame
            if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
                return {"success": True, "status": "success", "message": "Music stopped."}
            return {"success": True, "status": "success", "message": "No music is playing."}
        except Exception as e:
            return {"success": False, "status": "error", "message": str(e)}

    # Extract search query
    query = target_lower
    for prefix in ["play some ", "play ", "music "]:
        if query.startswith(prefix):
            query = query[len(prefix):]
            break

    if not query or query in ("music", "song", "songs", "beats"):
        query = "lofi hip hop beats"

    # Play in background thread
    threading.Thread(target=_search_and_play, args=[query], daemon=True).start()

    return {
        "success": True,
        "status": "success",
        "message": f"Searching and playing: {query}",
        "output": query,
    }
