"""
passpasspasspass of src/utils/cronTasksLock
"""
from __future__ import annotations

import os
import pathlib
import time
from typing import Any, Optional, TypedDict

from ..bootstrap.state import getProjectRoot, getSessionId
from .cleanupRegistry import register_cleanup
from .debug import logForDebugging
from .errors import get_errno_code
from .genericProcessUtils import isProcessRunning
from .json import parse_json
from .slowOperations import jsonStringify

LOCK_FILE_REL = os.path.join('.vivian', 'scheduled_tasks.lock')


class SchedulerLock(TypedDict):
    sessionId: str
    pid: int
    acquiredAt: int


class SchedulerLockOptions(TypedDict, total=False):
    dir: str
    lockIdentity: str


_unregister_cleanup: Optional[callable] = None
_last_blocked_by: Optional[str] = None


def getLockPath(dir=None):
    return os.path.join(dir or getProjectRoot(), LOCK_FILE_REL)


async def readLock(dir=None):
    raw = None
    try:
        with open(getLockPath(dir), 'r', encoding='utf-8') as handle:
            raw = handle.read()
    except Exception:
        return None
    parsed = parse_json(raw, None)
    if not isinstance(parsed, dict):
        return None
    session_id = parsed.get('sessionId')
    pid = parsed.get('pid')
    acquired_at = parsed.get('acquiredAt')
    if not isinstance(session_id, str) or not isinstance(pid, int) or not isinstance(acquired_at, int):
        return None
    return {'sessionId': session_id, 'pid': pid, 'acquiredAt': acquired_at}


async def tryCreateExclusive(lock, dir=None):
    path = getLockPath(dir)
    body = jsonStringify(lock)
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o666)
        with os.fdopen(descriptor, 'w', encoding='utf-8') as handle:
            handle.write(body)
        return True
    except OSError as error:
        code = get_errno_code(error)
        if code == 'EEXIST':
            return False
        if code == 'ENOENT':
            pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
            try:
                descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o666)
                with os.fdopen(descriptor, 'w', encoding='utf-8') as handle:
                    handle.write(body)
                return True
            except OSError as retry_error:
                if get_errno_code(retry_error) == 'EEXIST':
                    return False
                raise
        raise


def registerLockCleanup(opts=None):
    global _unregister_cleanup
    if _unregister_cleanup is not None:
        _unregister_cleanup()
    _unregister_cleanup = register_cleanup(lambda: releaseSchedulerLock(opts))


async def tryAcquireSchedulerLock(opts=None):
    """Try to acquire the scheduler lock for the current session."""
    global _last_blocked_by
    opts = opts or {}
    dir = opts.get('dir')
    session_id = opts.get('lockIdentity') or getSessionId()
    lock: SchedulerLock = {
        'sessionId': session_id,
        'pid': os.getpid(),
        'acquiredAt': int(time.time() * 1000),
    }

    if await tryCreateExclusive(lock, dir):
        _last_blocked_by = None
        registerLockCleanup(opts)
        logForDebugging(f'[ScheduledTasks] acquired scheduler lock (PID {os.getpid()})')
        return True

    existing = await readLock(dir)
    if existing and existing.get('sessionId') == session_id:
        if existing.get('pid') != os.getpid():
            with open(getLockPath(dir), 'w', encoding='utf-8') as handle:
                handle.write(jsonStringify(lock))
            registerLockCleanup(opts)
        return True

    if existing and isProcessRunning(existing.get('pid')):
        if _last_blocked_by != existing.get('sessionId'):
            _last_blocked_by = existing.get('sessionId')
            logForDebugging(
                f'[ScheduledTasks] scheduler lock held by session {existing.get("sessionId")} (PID {existing.get("pid")})'
            )
        return False

    if existing:
        logForDebugging(
            f'[ScheduledTasks] recovering stale scheduler lock from PID {existing.get("pid")}'
        )
    try:
        os.unlink(getLockPath(dir))
    except OSError:
        pass
    if await tryCreateExclusive(lock, dir):
        _last_blocked_by = None
        registerLockCleanup(opts)
        return True
    return False


async def releaseSchedulerLock(opts=None):
    """Release the scheduler lock if the current session owns it."""
    global _unregister_cleanup, _last_blocked_by
    if _unregister_cleanup is not None:
        _unregister_cleanup()
        _unregister_cleanup = None
    _last_blocked_by = None

    opts = opts or {}
    dir = opts.get('dir')
    session_id = opts.get('lockIdentity') or getSessionId()
    existing = await readLock(dir)
    if not existing or existing.get('sessionId') != session_id:
        return None
    try:
        os.unlink(getLockPath(dir))
        logForDebugging('[ScheduledTasks] released scheduler lock')
    except OSError:
        pass
    return None


get_lock_path = getLockPath
read_lock = readLock
try_create_exclusive = tryCreateExclusive
register_lock_cleanup = registerLockCleanup
try_acquire_scheduler_lock = tryAcquireSchedulerLock
release_scheduler_lock = releaseSchedulerLock

