"""Small durable filesystem primitives used by effectful Workspace adapters."""

from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import threading
from typing import Iterator

try:  # pragma: no cover - exercised on Unix CI; fallback supports import elsewhere.
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None


_LOCKS_GUARD = threading.Lock()
_LOCKS: dict[str, threading.RLock] = {}


def _thread_lock(path: Path) -> threading.RLock:
    key = str(path.resolve())
    with _LOCKS_GUARD:
        return _LOCKS.setdefault(key, threading.RLock())


@contextmanager
def file_mutex(path: Path) -> Iterator[None]:
    """Serialize threads and processes that mutate one Workspace resource."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = _thread_lock(path)
    with lock:
        descriptor = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            if fcntl is not None:
                fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)


def atomic_write(path: Path, data: bytes) -> None:
    """Replace one file atomically after flushing its content."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        os.close(descriptor)
    os.replace(temporary, path)
    try:
        directory = os.open(path.parent, os.O_RDONLY)
    except OSError:  # pragma: no cover - unusual platform/filesystem.
        return
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
