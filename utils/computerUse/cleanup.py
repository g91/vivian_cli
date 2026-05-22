"""Port of src/utils/computerUse/cleanup.ts."""
from __future__ import annotations

import asyncio

from ..debug import logForDebugging
from ..errors import errorMessage
from .computerUseLock import isLockHeldLocally, releaseComputerUseLock
from .escHotkey import unregisterEscHotkey


UNHIDE_TIMEOUT_MS = 5000


async def cleanupComputerUseAfterTurn(ctx):
    app_state = ctx.getAppState()
    hidden = None
    if isinstance(app_state, dict):
        hidden = ((app_state.get("computerUseMcpState") or {}).get("hiddenDuringTurn"))
    else:
        cu_state = getattr(app_state, "computerUseMcpState", None)
        hidden = getattr(cu_state, "hiddenDuringTurn", None) if cu_state is not None else None

    if hidden:
        from .executor import unhideComputerUseApps

        async def _unhide():
            try:
                await unhideComputerUseApps(list(hidden))
            except Exception as err:
                logForDebugging(f"[Computer Use MCP] auto-unhide failed: {errorMessage(err)}")

        try:
            await asyncio.wait_for(_unhide(), timeout=UNHIDE_TIMEOUT_MS / 1000)
        except asyncio.TimeoutError:
            _timed_out = True

        def _clear_hidden(prev):
            if isinstance(prev, dict):
                cu = dict(prev.get("computerUseMcpState") or {})
                if cu.get("hiddenDuringTurn") is None:
                    return prev
                cu["hiddenDuringTurn"] = None
                return {**prev, "computerUseMcpState": cu}
            return prev

        ctx.setAppState(_clear_hidden)

    if not isLockHeldLocally():
        return

    try:
        unregisterEscHotkey()
    except Exception as err:
        logForDebugging(f"[Computer Use MCP] unregisterEscHotkey failed: {errorMessage(err)}")

    if await releaseComputerUseLock():
        send = getattr(ctx, "sendOSNotification", None)
        if callable(send):
            send({"message": "vivian is done using your computer", "notificationType": "computer_use_exit"})


cleanup_computer_use_after_turn = cleanupComputerUseAfterTurn

