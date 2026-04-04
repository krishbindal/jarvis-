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

def get_logger(name: str) -> logging.Logger:
    """Return a logger with pre-configured multi-output handlers."""
    return logging.getLogger(name)
