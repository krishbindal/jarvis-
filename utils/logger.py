from __future__ import annotations

"""Centralized logging configuration."""

import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
