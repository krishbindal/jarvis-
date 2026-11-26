"""
JARVIS-X Phase 23: Autonomous File Sorcerer
Self-managing file organizer for Downloads and Desktop.
"""

from __future__ import annotations

import os
import shutil
import time
import threading
from pathlib import Path
from typing import Optional

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from utils.logger import get_logger
from brain.ai_engine import query_ai

logger = get_logger(__name__)

# Categories Configuration
CATEGORIES = {
    "Documents": [".pdf", ".docx", ".doc", ".txt", ".pptx", ".xlsx", ".csv"],
    "Images": [".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp"],
    "Executables": [".exe", ".msi", ".bat", ".sh"],
    "Media": [".mp3", ".wav", ".mp4", ".mov", ".mkv", ".avi"],
    "Archives": [".zip", ".rar", ".7z", ".tar", ".gz"],
    "Code": [".py", ".js", ".html", ".css", ".java", ".c", ".cpp", ".json"]
}

class FileSorceringHandler(FileSystemEventHandler):
    """Handles file creation events by moving items into sorted subfolders."""
    
    def __init__(self, watch_path: str, event_bus):
        self.watch_path = Path(watch_path)
        self.event_bus = event_bus

    def on_created(self, event):
        if not event.is_directory:
            self._handle_new_file(Path(event.src_path))

    def on_moved(self, event):
        # Browsers commonly rename .crdownload/.part to the final filename.
        if not event.is_directory:
            self._handle_new_file(Path(event.dest_path))

    def _handle_new_file(self, file_path: Path) -> None:
        # Never relocate an in-progress or hidden temporary download.
        if (
            file_path.name.startswith(".")
            or file_path.suffix.lower() in {".part", ".crdownload", ".download", ".tmp"}
            or file_path.parent != self.watch_path
        ):
            return
        time.sleep(2)
        if not file_path.is_file() or file_path.is_symlink():
            return
        # If still growing, defer to a later event rather than move a partial file.
        try:
            first_size = file_path.stat().st_size
            time.sleep(0.2)
            if not file_path.is_file() or file_path.stat().st_size != first_size:
                logger.info("[SORCERER] Skipping file still being written")
                return
        except OSError:
            return
        self._sort_file(file_path)

    def _sort_file(self, file_path: Path):
        ext = file_path.suffix.lower()
        target_folder = "Others"
        
        for category, extensions in CATEGORIES.items():
            if ext in extensions:
                target_folder = category
                break
        
        # Create 'Sorted' subfolder in the watched directory
        base_sorted = self.watch_path / "Jarvis_Sorted"
        dest_dir = base_sorted / target_folder
        
        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
            
            # Smart Renaming if it's a generic generic name
            new_name = file_path.name
            if len(file_path.stem) < 5 and file_path.stem.isdigit():
                 # Example: 1234.pdf -> 2024-04-04_1234.pdf
                 timestamp = time.strftime("%Y-%m-%d")
                 new_name = f"{timestamp}_{file_path.name}"
            
            dest_path = dest_dir / new_name

            # Never overwrite a previously sorted file on a name collision.
            stem, suffix = Path(new_name).stem, Path(new_name).suffix
            for n in range(1, 1001):
                if not dest_path.exists():
                    break
                dest_path = dest_dir / f"{stem} ({n}){suffix}"
            if dest_path.exists():
                logger.warning("[SORCERER] Collision limit reached: %s", new_name)
                return

            shutil.move(str(file_path), str(dest_path))
            logger.info(f"[SORCERER] Organized: {file_path.name} -> {target_folder}/")
            
            self.event_bus.emit("file_sorted", {
                "original": file_path.name,
                "category": target_folder,
                "path": str(dest_path)
            })
            
        except Exception as e:
            logger.error(f"[SORCERER] Failed to move {file_path.name}: {e}")

class FileSorcerer:
    """Manages watchers for Desktop and Downloads."""
    
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.observer = Observer()
        self._running = False
        
        self.targets = [
            str(Path.home() / "Downloads"),
            str(Path.home() / "Desktop")
        ]

    def start(self):
        if self._running:
            return
        
        for t in self.targets:
            if os.path.exists(t):
                handler = FileSorceringHandler(t, self.event_bus)
                self.observer.schedule(handler, t, recursive=False)
                logger.info(f"[SORCERER] Watching: {t}")
        
        self.observer.start()
        self._running = True

    def stop(self):
        if not self._running:
            return
        self.observer.stop()
        self.observer.join()
        self._running = False
        logger.info("[SORCERER] Watchers stopped.")
