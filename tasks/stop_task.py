"""Compatibility wrapper for exact-case stopTask module."""

from __future__ import annotations

import asyncio

from .stopTask import StopTaskError, stopTask


def stop_task(task_id, get_app_state, set_app_state):
    return asyncio.run(stopTask(task_id, {"getAppState": get_app_state, "setAppState": set_app_state}))


__all__ = ["StopTaskError", "stopTask", "stop_task"]
