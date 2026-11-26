"""Bounded downloads with URL, redirect, filename and atomic-file safeguards."""
from __future__ import annotations

import ipaddress
import os
import socket
import tempfile
from pathlib import Path
from typing import Dict
from urllib.parse import urljoin, urlparse, unquote

import requests
import yt_dlp

from utils.logger import get_logger
from config import REQUEST_TIMEOUT, DOWNLOAD_DIR, MAX_DOWNLOAD_BYTES

DEFAULT_DOWNLOAD_DIR = Path(DOWNLOAD_DIR).expanduser().resolve()
logger = get_logger(__name__)
_MAX_REDIRECTS = 5
_REDIRECT_CODES = {301, 302, 303, 307, 308}
_YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be", "www.youtu.be"}


def _is_public_host(host: str) -> bool:
    """Reject non-global DNS answers. This is not a DNS-rebinding-proof sandbox."""
    try:
        infos = socket.getaddrinfo(host, None)
        return bool(infos) and all(
            ipaddress.ip_address(info[4][0]).is_global for info in infos
        )
    except (OSError, ValueError):
        return False


def _validate_url(url: str) -> str | None:
    if not isinstance(url, str) or not url or len(url) > 2048:
        return "URL must be a nonempty http(s) address under 2048 characters."
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return "Only http/https URLs are allowed."
        if not parsed.hostname:
            return "URL is missing a hostname."
        if parsed.username is not None or parsed.password is not None:
            return "Embedded URL credentials are not permitted."
        if not _is_public_host(parsed.hostname):
            return "Refusing a private, internal, or unresolvable download host."
    except ValueError:
        return "Malformed download URL."
    return None


def _safe_name(raw: str, suffix: str | None = None) -> str:
    name = Path(unquote(raw)).name or "download"
    name = name.replace("\\", "_").replace("/", "_").strip().lstrip(".")
    name = "".join(c for c in name if c.isalnum() or c in " ._-")[:180] or "download"
    if suffix:
        name = str(Path(name).with_suffix(suffix if suffix.startswith(".") else f".{suffix}"))
    return name


def _save_path_from_url(url: str, suffix: str | None = None) -> Path:
    parsed = urlparse(url)
    name = _safe_name(parsed.path.rsplit("/", 1)[-1] or "download", suffix)
    resolved = (DEFAULT_DOWNLOAD_DIR / name).resolve()
    resolved.relative_to(DEFAULT_DOWNLOAD_DIR)
    return resolved


def _persist_no_overwrite(temp_path: Path, desired_path: Path) -> Path:
    """Link completed temporary file to an available name, without overwriting.

    Because temporary and final paths share a directory, hard links are normally
    available on NTFS and POSIX filesystems. Fail closed if unsupported.
    """
    stem, suffix = desired_path.stem, desired_path.suffix
    for number in range(1000):
        dest = desired_path if number == 0 else desired_path.with_name(f"{stem} ({number}){suffix}")
        try:
            os.link(temp_path, dest)
            return dest
        except FileExistsError:
            continue
    raise FileExistsError("No free filename available (1000 collisions).")


def download_file(url: str) -> Dict:
    error = _validate_url(url)
    if error:
        return {"success": False, "status": "invalid_url", "message": error}

    DEFAULT_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    temp_path = None
    current = url
    try:
        for hop in range(_MAX_REDIRECTS + 1):
            redirect = None
            # requests follows redirects by default; explicitly disable that so
            # every Location receives the same public-host validation.
            with requests.get(current, stream=True, timeout=REQUEST_TIMEOUT, allow_redirects=False) as response:
                if response.status_code in _REDIRECT_CODES:
                    redirect = response.headers.get("Location")
                    if not redirect:
                        return {"success": False, "status": "invalid_redirect", "message": "Download redirect has no destination."}
                else:
                    response.raise_for_status()
                    declared = int(response.headers.get("Content-Length", "0") or "0")
                    if declared > MAX_DOWNLOAD_BYTES:
                        return {"success": False, "status": "too_large", "message": "Download exceeds the configured size limit."}
                    fd, name = tempfile.mkstemp(prefix=".jarvis-", suffix=".part", dir=DEFAULT_DOWNLOAD_DIR)
                    temp_path = Path(name)
                    total = 0
                    with os.fdopen(fd, "wb") as stream:
                        for chunk in response.iter_content(chunk_size=8192):
                            if not chunk:
                                continue
                            total += len(chunk)
                            if total > MAX_DOWNLOAD_BYTES:
                                return {"success": False, "status": "too_large", "message": "Download exceeded the configured size limit."}
                            stream.write(chunk)
                    destination = _persist_no_overwrite(temp_path, _save_path_from_url(current))
                    return {
                        "success": True,
                        "status": "success",
                        "message": f"Downloaded {total} bytes to {destination}.",
                        "path": str(destination),
                        "output": str(destination),
                        "bytes_written": total,
                    }

            if redirect is not None:
                if hop >= _MAX_REDIRECTS:
                    return {"success": False, "status": "too_many_redirects", "message": "Download redirect limit reached."}
                candidate = urljoin(current, redirect)
                error = _validate_url(candidate)
                if error:
                    return {"success": False, "status": "blocked_redirect", "message": f"Unsafe redirect blocked: {error}"}
                current = candidate

        return {"success": False, "status": "too_many_redirects", "message": "Download redirect limit reached."}
    except (requests.RequestException, OSError, ValueError) as exc:
        logger.warning("[DOWNLOAD] Failed (%s)", type(exc).__name__)
        return {"success": False, "status": "error", "message": f"Download failed ({type(exc).__name__})."}
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def download_video(url: str) -> Dict:
    """Limit the yt-dlp entry URL to a known media site; still not a network sandbox."""
    err = _validate_url(url)
    if err:
        return {"success": False, "status": "invalid_url", "message": err}
    try:
        host = urlparse(url).hostname
    except ValueError:
        host = None
    if host not in _YOUTUBE_HOSTS:
        return {
            "success": False, "status": "unsupported_host",
            "message": "Video downloads are restricted to YouTube URLs.",
        }
    try:
        DEFAULT_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
        with yt_dlp.YoutubeDL({
            "outtmpl": str(DEFAULT_DOWNLOAD_DIR / "%(title)s.%(ext)s"),
            "restrictfilenames": True,
            "noplaylist": True,
            "max_filesize": MAX_DOWNLOAD_BYTES,
            "quiet": True,
            "noprogress": True,
        }) as ydl:
            info = ydl.extract_info(url, download=True)
            if not isinstance(info, dict):
                raise RuntimeError("No video information was returned")
            filename = ydl.prepare_filename(info)
        if not Path(filename).is_file():
            return {"success": False, "status": "unverified", "message": "Video downloader returned but output file could not be found."}
        return {
            "success": True,
            "status": "success",
            "message": f"Video file exists at {filename}; playback was not verified.",
            "path": filename, "output": filename,
        }
    except Exception as exc:
        logger.warning("[DOWNLOAD] Video download failed (%s)", type(exc).__name__)
        return {"success": False, "status": "error", "message": "Video download failed; inspect the local logs."}
