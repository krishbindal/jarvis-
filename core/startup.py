from __future__ import annotations

import time
from pathlib import Path

import pygame

STARTUP_SOUND = Path(__file__).resolve().parent.parent / "assets" / "sounds" / "startup.mp3"


def _init_mixer() -> bool:
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"Startup audio init failed: {exc}")
        return False


def _play_blocking(path: Path) -> None:
    """Play the provided audio file and block until completion."""
    pygame.mixer.music.load(str(path))
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
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
            pygame.mixer.quit()
        except Exception:
            pass
