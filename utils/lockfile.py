"""File locking utilities — mirrors src/utils/lockfile.ts"""
from __future__ import annotations

import os
from typing import Callable, Optional

try:
    from filelock import FileLock, Timeout as FileLockTimeout
    _HAS_FILELOCK = True
except ImportError:
    _HAS_FILELOCK = False


def lock(
    file: str,
    *,
    timeout_ms: int = 10_000,
    retries: int = 0,
) -> Callable[[], None]:
    """Acquire an exclusive lock on ``file``.

    Returns a callable that releases the lock when called.
    Raises ``OSError`` if the lock cannot be acquired within the timeout.

    Requires the ``filelock`` package (``pip install filelock``).
    """
    if not _HAS_FILELOCK:
        raise ImportError("filelock package required: pip install filelock")
    fl = FileLock(file + ".lock")
    try:
        fl.acquire(timeout=timeout_ms / 1000)
    except FileLockTimeout as e:
        raise OSError(f"Could not acquire lock on {file}: {e}") from e
    return fl.release


def unlock(file: str) -> None:
    """Release an exclusive lock on ``file``.

    Silently ignores errors (already unlocked etc.).
    """
    lock_path = file + ".lock"
    try:
        os.remove(lock_path)
    except OSError:
        pass


def check(file: str) -> bool:
    """Return True if the file is currently locked (i.e. lock file exists).

    Non-blocking check — does not attempt to acquire the lock.
    """
    return os.path.exists(file + ".lock")
