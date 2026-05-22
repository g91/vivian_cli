"""Port of src/utils/computerUse/hostAdapter.ts."""
from __future__ import annotations

from ..debug import logForDebugging
from .common import COMPUTER_USE_MCP_SERVER_NAME
from .gates import getChicagoEnabled, getChicagoSubGates
from .swiftLoader import requireComputerUseSwift


class DebugLogger:
    def silly(self, message: str, *args):
        logForDebugging(message % args if args else message, level="debug")

    def debug(self, message: str, *args):
        logForDebugging(message % args if args else message, level="debug")

    def info(self, message: str, *args):
        logForDebugging(message % args if args else message, level="info")

    def warn(self, message: str, *args):
        logForDebugging(message % args if args else message, level="warn")

    def error(self, message: str, *args):
        logForDebugging(message % args if args else message, level="error")


_cached = None


def getComputerUseHostAdapter():
    global _cached
    if _cached is not None:
        return _cached
    from .executor import createCliExecutor

    _cached = {
        "serverName": COMPUTER_USE_MCP_SERVER_NAME,
        "logger": DebugLogger(),
        "executor": createCliExecutor(
            {
                "getMouseAnimationEnabled": lambda: getChicagoSubGates().get("mouseAnimation", True),
                "getHideBeforeActionEnabled": lambda: getChicagoSubGates().get("hideBeforeAction", True),
            }
        ),
        "ensureOsPermissions": lambda: _ensure_os_permissions(),
        "isDisabled": lambda: not getChicagoEnabled(),
        "getSubGates": getChicagoSubGates,
        "getAutoUnhideEnabled": lambda: True,
        "cropRawPatch": lambda *_args, **_kwargs: None,
    }
    return _cached


async def _ensure_os_permissions():
    cu = requireComputerUseSwift()
    accessibility = cu.tcc.checkAccessibility()
    screen_recording = cu.tcc.checkScreenRecording()
    if accessibility and screen_recording:
        return {"granted": True}
    return {
        "granted": False,
        "accessibility": accessibility,
        "screenRecording": screen_recording,
    }


get_computer_use_host_adapter = getComputerUseHostAdapter

