"""Port of src/utils/computerUse/escHotkey.ts."""
from __future__ import annotations

from ..debug import logForDebugging
from .drainRunLoop import releasePump, retainPump
from .swiftLoader import requireComputerUseSwift


registered = False


def registerEscHotkey(onEscape=None):
    global registered
    if registered:
        return True
    cu = requireComputerUseSwift()
    if not cu.hotkey.registerEscape(onEscape):
        logForDebugging("[cu-esc] registerEscape returned false", level="warn")
        return False
    retainPump()
    registered = True
    logForDebugging("[cu-esc] registered")
    return True


def unregisterEscHotkey():
    global registered
    if not registered:
        return
    try:
        requireComputerUseSwift().hotkey.unregister()
    finally:
        releasePump()
        registered = False
        logForDebugging("[cu-esc] unregistered")


def notifyExpectedEscape():
    if not registered:
        return
    requireComputerUseSwift().hotkey.notifyExpectedEscape()

