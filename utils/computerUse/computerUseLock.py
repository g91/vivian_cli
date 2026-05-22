"""Port of src/utils/computerUse/computerUseLock.ts."""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

from ...bootstrap.state import getSessionId
from ..cleanupRegistry import register_cleanup
from ..debug import logForDebugging
from ..envUtils import get_vivian_config_home_dir


LOCK_FILENAME = "computer-use.lock"
_unregister_cleanup = None
FRESH = {"kind": "acquired", "fresh": True}
REENTRANT = {"kind": "acquired", "fresh": False}


def isComputerUseLock(value):
    return (
        isinstance(value, dict)
        and isinstance(value.get("sessionId"), str)
        and isinstance(value.get("pid"), int)
    )


def getLockPath():
    return str(Path(get_vivian_config_home_dir()) / LOCK_FILENAME)


async def readLock():
    try:
        raw = await asyncio.to_thread(Path(getLockPath()).read_text, encoding="utf-8")
        parsed = json.loads(raw)
        return parsed if isComputerUseLock(parsed) else None
    except Exception:
        return None


def isProcessRunning(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except Exception:
        return False


async def tryCreateExclusive(lock):
    def _write() -> bool:
        try:
            fd = os.open(getLockPath(), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(lock, handle)
            return True
        except FileExistsError:
            return False

    return await asyncio.to_thread(_write)


def registerLockCleanup():
    global _unregister_cleanup
    if _unregister_cleanup is not None:
        _unregister_cleanup()
    _unregister_cleanup = register_cleanup(releaseComputerUseLock)


async def checkComputerUseLock():
    existing = await readLock()
    if not existing:
        return {"kind": "free"}
    if existing["sessionId"] == getSessionId():
        return {"kind": "held_by_self"}
    if isProcessRunning(existing["pid"]):
        return {"kind": "blocked", "by": existing["sessionId"]}
    logForDebugging(
        f"Recovering stale computer-use lock from session {existing['sessionId']} (PID {existing['pid']})"
    )
    await asyncio.to_thread(Path(getLockPath()).unlink, missing_ok=True)
    return {"kind": "free"}


def isLockHeldLocally():
    return _unregister_cleanup is not None


async def tryAcquireComputerUseLock():
    session_id = getSessionId()
    lock = {"sessionId": session_id, "pid": os.getpid(), "acquiredAt": int(asyncio.get_event_loop().time() * 1000)}
    Path(get_vivian_config_home_dir()).mkdir(parents=True, exist_ok=True)
    if await tryCreateExclusive(lock):
        registerLockCleanup()
        return dict(FRESH)
    existing = await readLock()
    if not existing:
        await asyncio.to_thread(Path(getLockPath()).unlink, missing_ok=True)
        if await tryCreateExclusive(lock):
            registerLockCleanup()
            return dict(FRESH)
        winner = await readLock()
        return {"kind": "blocked", "by": winner.get("sessionId", "unknown") if winner else "unknown"}
    if existing["sessionId"] == session_id:
        return dict(REENTRANT)
    if isProcessRunning(existing["pid"]):
        return {"kind": "blocked", "by": existing["sessionId"]}
    logForDebugging(
        f"Recovering stale computer-use lock from session {existing['sessionId']} (PID {existing['pid']})"
    )
    await asyncio.to_thread(Path(getLockPath()).unlink, missing_ok=True)
    if await tryCreateExclusive(lock):
        registerLockCleanup()
        return dict(FRESH)
    winner = await readLock()
    return {"kind": "blocked", "by": winner.get("sessionId", "unknown") if winner else "unknown"}


async def releaseComputerUseLock():
    global _unregister_cleanup
    if _unregister_cleanup is not None:
        _unregister_cleanup()
        _unregister_cleanup = None
    existing = await readLock()
    if not existing or existing["sessionId"] != getSessionId():
        return False
    try:
        await asyncio.to_thread(Path(getLockPath()).unlink, missing_ok=True)
        logForDebugging("Released computer-use lock")
        return True
    except Exception:
        return False


is_computer_use_lock = isComputerUseLock
get_lock_path = getLockPath
read_lock = readLock
is_process_running = isProcessRunning
try_create_exclusive = tryCreateExclusive
register_lock_cleanup = registerLockCleanup
check_computer_use_lock = checkComputerUseLock
is_lock_held_locally = isLockHeldLocally
try_acquire_computer_use_lock = tryAcquireComputerUseLock
release_computer_use_lock = releaseComputerUseLock

