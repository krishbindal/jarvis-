from __future__ import annotations

"""Network download executor with SSRF and path-traversal protections."""

import ipaddress
import socket
from pathlib import Path
from typing import Dict
from urllib.parse import urlparse, unquote

import requests
import yt_dlp
from utils.logger import get_logger
from config import REQUEST_TIMEOUT, DOWNLOAD_DIR, MAX_DOWNLOAD_BYTES

DEFAULT_DOWNLOAD_DIR = Path(DOWNLOAD_DIR).expanduser().resolve()
DEFAULT_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

logger = get_logger(__name__)


def _is_public_host(host: str) -> bool:
    """Resolve host and reject private/loopback/link-local addresses (SSRF guard)."""
    try:
        infos = socket.getaddrinfo(host, None)
    except Exception:  # noqa: BLE001
        return False
    for info in infos:
        addr = info[4][0]
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            return False
        if (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_multicast or ip.is_reserved or ip.is_unspecified):
            return False
    return True


def _validate_url(url: str) -> str | None:
    """Return an error string if the URL is not a safe public http(s) URL."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return "Only http/https URLs are allowed."
    if not parsed.hostname:
        return "URL is missing a hostname."
    if not _is_public_host(parsed.hostname):
        return "Refusing to download from a private/internal address."
    return None


def _safe_name(raw: str, suffix: str | None = None) -> str:
    """Derive a filename that cannot escape the download directory."""
    name = Path(unquote(raw)).name or "download"
    # Strip anything that could enable traversal or hidden control chars.
    name = name.replace("\\", "_").replace("/", "_").strip().lstrip(".")
    name = "".join(c for c in name if c.isalnum() or c in " ._-") or "download"
    if suffix:
        name = str(Path(name).with_suffix(suffix if suffix.startswith(".") else f".{suffix}"))
    return name


def _save_path_from_url(url: str, suffix: str | None = None) -> Path:
    name = _safe_name(url.split("?")[0].split("/")[-1], suffix)
    resolved = (DEFAULT_DOWNLOAD_DIR / name).resolve()
    # Ensure the resolved path stays inside the download directory.
    resolved.relative_to(DEFAULT_DOWNLOAD_DIR)
    return resolved


def download_file(url: str) -> Dict:
    err = _validate_url(url)
    if err:
        logger.warning("Rejected download URL %s: %s", url, err)
        return {"success": False, "status": "error", "message": err}
    try:
        logger.info("Downloading file: %s", url)
        path = _save_path_from_url(url)
        written = 0
        with requests.get(url, stream=True, timeout=REQUEST_TIMEOUT) as resp:
            resp.raise_for_status()
            declared = int(resp.headers.get("Content-Length", 0) or 0)
            if declared and declared > MAX_DOWNLOAD_BYTES:
                return {"success": False, "status": "error",
                        "message": f"File too large ({declared} bytes > {MAX_DOWNLOAD_BYTES})."}
            with path.open("wb") as fh:
                for chunk in resp.iter_content(chunk_size=8192):
                    if not chunk:
                        continue
                    written += len(chunk)
                    if written > MAX_DOWNLOAD_BYTES:
                        fh.close()
                        path.unlink(missing_ok=True)
                        return {"success": False, "status": "error",
                                "message": f"Download exceeded size limit of {MAX_DOWNLOAD_BYTES} bytes."}
                    fh.write(chunk)
        return {
            "success": True,
            "status": "success",
            "message": f"Download complete: {path}",
            "path": str(path),
            "output": str(path),
        }
    except requests.Timeout:
        logger.error("Download timed out for %s", url)
        return {"success": False, "status": "error", "output": "Request timed out", "message": "Request timed out"}
    except Exception as exc:  # noqa: BLE001
        logger.error("Download failed for %s: %s", url, exc)
        return {"success": False, "status": "error", "message": f"Download failed: {exc}"}


def download_video(url: str) -> Dict:
    err = _validate_url(url)
    if err:
        logger.warning("Rejected video URL %s: %s", url, err)
        return {"success": False, "status": "error", "message": err}
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
