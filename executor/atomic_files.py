"""Atomic no-overwrite publication for user file operations.

Uses hard links on the same filesystem. This deliberately fails closed when
filesystem semantics or permissions do not support hard links, rather than
silently falling back to an overwrite-capable rename/copy.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import tempfile


class StagingVerificationError(OSError):
    """A staging copy did not produce the complete expected file."""


class SourceRemovalError(OSError):
    """Destination was published but source unlink failed: partial move."""

    def __init__(self, source: Path, destination: Path):
        super().__init__(
            f"Published {destination.name} but could not remove source {source.name}. "
            "Both files may exist; inspect them manually."
        )
        self.source = source
        self.destination = destination


def copy_file_no_overwrite(source: Path, destination: Path) -> None:
    """Copy bytes into a same-directory staging file, then publish atomically."""
    source, destination = Path(source), Path(destination)
    if not source.is_file():
        raise FileNotFoundError("Source is not a regular file.")
    if destination == source:
        raise FileExistsError("Source and destination cannot be the same.")
    if not destination.parent.is_dir():
        raise FileNotFoundError("Destination directory does not exist.")

    fd, name = tempfile.mkstemp(prefix=".jarvis-copy-", suffix=".part", dir=destination.parent)
    staged = Path(name)
    os.close(fd)
    try:
        shutil.copy2(source, staged)
        if not staged.is_file() or staged.stat().st_size != source.stat().st_size:
            raise StagingVerificationError("Staged file size does not match the source.")
        # Fails atomically with FileExistsError if another writer won the race.
        os.link(staged, destination)
    finally:
        staged.unlink(missing_ok=True)


def move_file_no_overwrite(source: Path, destination: Path) -> None:
    """Publish same-filesystem regular file without replacing anything."""
    source, destination = Path(source), Path(destination)
    if not source.is_file():
        raise FileNotFoundError("Source is not a regular file.")
    if destination == source:
        raise FileExistsError("Source and destination cannot be the same.")
    if not destination.parent.is_dir():
        raise FileNotFoundError("Destination directory does not exist.")
    # The destination filename is allocated atomically by the OS.
    # EXDEV, lack of hardlink privileges and network filesystems fail closed.
    os.link(source, destination)
    try:
        source.unlink()
    except OSError as exc:
        raise SourceRemovalError(source, destination) from exc
