from __future__ import annotations

"""
Centralized logging configuration with simultaneous console and 
persistent file logging for the Sentinel Fixer autonomous daemon.
"""

import logging
import os
from pathlib import Path

# Ensure logs directory exists
LOG_DIR = Path("assets/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "jarvis.log"

# Multi-handler configuration
log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# File handler for Sentinel Fixer to tail
file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
file_handler.setFormatter(logging.Formatter(log_format))
file_handler.setLevel(logging.INFO)

# Stream handler for console feedback
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(logging.Formatter(log_format))
stream_handler.setLevel(logging.INFO)

# Root logger setup
logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, stream_handler]
)

class SentinelLogger:
    """Enhanced logger for JARVIS-X with structured tags."""
    def __init__(self, name: str):
        self._logger = logging.getLogger(name)

    def debug(self, msg: str, *args, **kwargs):
        self._logger.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs):
        self._logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs):
        self._logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs):
        self._logger.error(f"[ERROR] {msg}", *args, **kwargs)

    def critical(self, msg: str, *args, **kwargs):
        self._logger.critical(f"[CRITICAL] {msg}", *args, **kwargs)

    # Structured Tags
    def input(self, msg: str):
        self._logger.info(f"[INPUT] {msg}")

    def parsed(self, msg: str):
        self._logger.info(f"[PARSED] {msg}")

    def action(self, msg: str):
        self._logger.info(f"[ACTION] {msg}")

    def execution(self, msg: str):
        self._logger.info(f"[EXECUTION] {msg}")


def get_logger(name: str) -> SentinelLogger:
    """Return a SentinelLogger with pre-configured handlers."""
    return SentinelLogger(name)
