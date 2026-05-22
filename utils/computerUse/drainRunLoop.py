"""Port of src/utils/computerUse/drainRunLoop.ts."""
from __future__ import annotations

import asyncio

from ..debug import logForDebugging
from .swiftLoader import requireComputerUseSwift


_pump_task = None
_pending = 0
TIMEOUT_MS = 30_000


async def _pump_loop():
    cu = requireComputerUseSwift()
    try:
        while True:
            drainTick(cu)
            await asyncio.sleep(0.001)
    except asyncio.CancelledError:
        raise


def drainTick(cu):
    cu._drainMainRunLoop()


def retain():
    global _pending, _pump_task
    _pending += 1
    if _pump_task is None:
        _pump_task = asyncio.create_task(_pump_loop())
        logForDebugging("[drainRunLoop] pump started", level="verbose")


def release():
    global _pending, _pump_task
    _pending -= 1
    if _pending <= 0:
        _pending = 0
        if _pump_task is not None:
            _pump_task.cancel()
            _pump_task = None
            logForDebugging("[drainRunLoop] pump stopped", level="verbose")


def timeoutReject():
    raise RuntimeError(f"computer-use native call exceeded {TIMEOUT_MS}ms")


async def drainRunLoop(fn=None):
    retain()
    try:
        if fn is None:
            return None
        work = fn()
        if asyncio.iscoroutine(work) or isinstance(work, asyncio.Future):
            return await asyncio.wait_for(work, TIMEOUT_MS / 1000)
        return work
    finally:
        release()


retainPump = retain
releasePump = release
drain_run_loop = drainRunLoop

