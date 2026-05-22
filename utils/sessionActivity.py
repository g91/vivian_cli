"""Session activity tracking with refcount-based heartbeat timer."""
from __future__ import annotations

import asyncio
import os
import time
from typing import Callable

from .cleanupRegistry import register_cleanup
from .diagLogs import logForDiagnosticsNoPII
from .envUtils import is_env_truthy


SESSION_ACTIVITY_INTERVAL_MS = 30_000
SessionActivityReason = str

activityCallback: Callable[[], None] | None = None
refcount = 0
activeReasons: dict[SessionActivityReason, int] = {}
oldestActivityStartedAt: int | None = None
heartbeatTimer: asyncio.Task | None = None
idleTimer: asyncio.TimerHandle | None = None
cleanupRegistered = False


async def _heartbeat_loop() -> None:
    global heartbeatTimer
    try:
        while True:
            await asyncio.sleep(SESSION_ACTIVITY_INTERVAL_MS / 1000)
            logForDiagnosticsNoPII('debug', 'session_keepalive_heartbeat', {'refcount': refcount})
            if is_env_truthy(os.environ.get('vivian_CODE_REMOTE_SEND_KEEPALIVES')) and activityCallback is not None:
                activityCallback()
    except asyncio.CancelledError:
        raise
    finally:
        if heartbeatTimer is not None and heartbeatTimer.done():
            heartbeatTimer = None


def _get_loop() -> asyncio.AbstractEventLoop | None:
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        return None


def startHeartbeatTimer() -> None:
    global heartbeatTimer
    clearIdleTimer()
    if heartbeatTimer is not None:
        heartbeatTimer.cancel()
    loop = _get_loop()
    if loop is None:
        return
    heartbeatTimer = loop.create_task(_heartbeat_loop())


def startIdleTimer() -> None:
    global idleTimer
    clearIdleTimer()
    if activityCallback is None:
        return
    loop = _get_loop()
    if loop is None:
        return

    def _on_idle() -> None:
        global idleTimer
        logForDiagnosticsNoPII('info', 'session_idle_30s')
        idleTimer = None

    idleTimer = loop.call_later(SESSION_ACTIVITY_INTERVAL_MS / 1000, _on_idle)


def clearIdleTimer() -> None:
    global idleTimer
    if idleTimer is not None:
        idleTimer.cancel()
        idleTimer = None


def registerSessionActivityCallback(cb: Callable[[], None] | None = None) -> None:
    global activityCallback
    activityCallback = cb
    if refcount > 0 and heartbeatTimer is None:
        startHeartbeatTimer()


def unregisterSessionActivityCallback() -> None:
    global activityCallback, heartbeatTimer
    activityCallback = None
    if heartbeatTimer is not None:
        heartbeatTimer.cancel()
        heartbeatTimer = None
    clearIdleTimer()


def sendSessionActivitySignal() -> None:
    if is_env_truthy(os.environ.get('vivian_CODE_REMOTE_SEND_KEEPALIVES')) and activityCallback is not None:
        activityCallback()


def isSessionActivityTrackingActive() -> bool:
    return activityCallback is not None


def startSessionActivity(reason: SessionActivityReason) -> None:
    """Increment the activity refcount. When it transitions from 0->1 and a callback"""
    global refcount, oldestActivityStartedAt, cleanupRegistered
    refcount += 1
    activeReasons[reason] = activeReasons.get(reason, 0) + 1
    if refcount == 1:
        oldestActivityStartedAt = int(time.time() * 1000)
        if activityCallback is not None and heartbeatTimer is None:
            startHeartbeatTimer()
    if not cleanupRegistered:
        cleanupRegistered = True

        async def _cleanup() -> None:
            logForDiagnosticsNoPII(
                'info',
                'session_activity_at_shutdown',
                {
                    'refcount': refcount,
                    'active': dict(activeReasons),
                    'oldest_activity_ms': (
                        int(time.time() * 1000) - oldestActivityStartedAt
                        if refcount > 0 and oldestActivityStartedAt is not None
                        else None
                    ),
                },
            )

        register_cleanup(_cleanup)


def stopSessionActivity(reason: SessionActivityReason) -> None:
    """Decrement the activity refcount. When it reaches 0, stop the heartbeat timer"""
    global refcount, heartbeatTimer
    if refcount > 0:
        refcount -= 1
    next_count = activeReasons.get(reason, 0) - 1
    if next_count > 0:
        activeReasons[reason] = next_count
    else:
        activeReasons.pop(reason, None)
    if refcount == 0 and heartbeatTimer is not None:
        heartbeatTimer.cancel()
        heartbeatTimer = None
        startIdleTimer()


start_heartbeat_timer = startHeartbeatTimer
start_idle_timer = startIdleTimer
clear_idle_timer = clearIdleTimer
register_session_activity_callback = registerSessionActivityCallback
unregister_session_activity_callback = unregisterSessionActivityCallback
send_session_activity_signal = sendSessionActivitySignal
is_session_activity_tracking_active = isSessionActivityTrackingActive
start_session_activity = startSessionActivity
stop_session_activity = stopSessionActivity

