"""Port of src/utils/swarm/leaderPermissionBridge.ts

Module-level bridge allowing the REPL to register its setToolUseConfirmQueue
and setToolPermissionContext functions for in-process teammates to use.
"""
from __future__ import annotations
from typing import Any, Callable, Optional

SetToolUseConfirmQueueFn = Optional[Callable]
SetToolPermissionContextFn = Optional[Callable]

_registered_setter: Optional[Callable] = None
_registered_permission_context_setter: Optional[Callable] = None


def registerLeaderToolUseConfirmQueue(setter: Callable) -> None:
    global _registered_setter
    _registered_setter = setter


def getLeaderToolUseConfirmQueue() -> Optional[Callable]:
    return _registered_setter


def unregisterLeaderToolUseConfirmQueue() -> None:
    global _registered_setter
    _registered_setter = None


def registerLeaderSetToolPermissionContext(setter: Callable) -> None:
    global _registered_permission_context_setter
    _registered_permission_context_setter = setter


def getLeaderSetToolPermissionContext() -> Optional[Callable]:
    return _registered_permission_context_setter


def unregisterLeaderSetToolPermissionContext() -> None:
    global _registered_permission_context_setter
    _registered_permission_context_setter = None
