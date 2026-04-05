from __future__ import annotations

"""Startup sequence utilities."""

import threading
import time
from pathlib import Path
from typing import Callable, Optional

import pygame

STARTUP_SOUND = Path(__file__).resolve().parent.parent / "jarvis music.mp3"


def _init_mixer() -> bool:
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"Startup audio init failed: {exc}")
        return False


def _play_blocking(path: Path) -> None:
    """Play the provided audio file and block until completion (max 10s)."""
    pygame.mixer.music.load(str(path))
    pygame.mixer.music.play()
    
    start_time = time.time()
    while pygame.mixer.music.get_busy():
        if time.time() - start_time > 10:
            pygame.mixer.music.fadeout(1500) # Smooth 1.5s fadeout
            break
        time.sleep(0.05)


def play_startup_sound() -> None:
    """Play the cinematic startup sound before launching UI."""
    if not STARTUP_SOUND.exists():
        print(f"Startup sound not found at {STARTUP_SOUND}; continuing without audio.")
        return

    if not _init_mixer():
        return

    try:
        _play_blocking(STARTUP_SOUND)
    except Exception as exc:  # noqa: BLE001
        print(f"Unable to play startup sound: {exc}")
    finally:
        try:
            pygame.mixer.music.stop()
            # Do NOT call mixer.quit() here, as it kills audio for the rest of the app.
        except Exception:
            pass


def start_startup_sequence(on_complete: Optional[Callable[[], None]] = None) -> threading.Thread:
    """Start the startup sound in a background thread to avoid UI blocking."""

    def _runner() -> None:
        try:
            play_startup_sound()
        finally:
            if on_complete:
                try:
                    on_complete()
                except Exception as exc:  # noqa: BLE001
                    print(f"Startup completion callback failed: {exc}")

    thread = threading.Thread(target=_runner, name="startup-audio", daemon=True)
    thread.start()
    return thread
