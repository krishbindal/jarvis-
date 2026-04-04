from __future__ import annotations

"""Network download executor."""

import os
from pathlib import Path
from typing import Dict

import requests
import yt_dlp
from utils.logger import get_logger

DEFAULT_DOWNLOAD_DIR = Path("~/Downloads").expanduser()
DEFAULT_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

logger = get_logger(__name__)


def _save_path_from_url(url: str, suffix: str | None = None) -> Path:
    name = Path(url.split("/")[-1] or "download")
    if suffix:
        name = name.with_suffix(suffix if suffix.startswith(".") else f".{suffix}")
    return (DEFAULT_DOWNLOAD_DIR / name).resolve()


def download_file(url: str) -> Dict:
    try:
        logger.info("Downloading file: %s", url)
        path = _save_path_from_url(url)
        with requests.get(url, stream=True, timeout=30) as resp:
            resp.raise_for_status()
            with path.open("wb") as fh:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        fh.write(chunk)
        return {
            "success": True,
            "status": "success",
            "message": f"Download complete: {path}",
            "path": str(path),
            "output": str(path),
        }
    except Exception as exc:  # noqa: BLE001
        logger.error("Download failed for %s: %s", url, exc)
        return {"success": False, "status": "error", "message": f"Download failed: {exc}"}


def download_video(url: str) -> Dict:
    try:
        logger.info("Downloading video: %s", url)
        out_tpl = str(DEFAULT_DOWNLOAD_DIR / "%(title)s.%(ext)s")
        ydl_opts = {
            "outtmpl": out_tpl,
            "quiet": True,
            "noprogress": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
        return {
            "success": True,
            "status": "success",
            "message": f"Download complete: {filename}",
            "path": filename,
            "output": filename,
        }
    except Exception as exc:  # noqa: BLE001
        logger.error("Video download failed for %s: %s", url, exc)
        return {"success": False, "status": "error", "message": f"Video download failed: {exc}"}
