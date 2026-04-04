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
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        # Give a small delay for file to be fully written (e.g. from browser download)
        time.sleep(2)
        
        if not file_path.exists():
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
            
            # Handle collision
            if dest_path.exists():
                dest_path = dest_dir / f"{int(time.time())}_{new_name}"
            
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
