"""Port of src/utils/sessionState.ts"""
from __future__ import annotations
from typing import Any, Callable, Dict, Optional

SessionState = str  # 'idle' | 'running' | 'requires_action'
RequiresActionDetails = Dict[str, Any]
SessionExternalMetadata = Dict[str, Any]

_state_listener: Optional[Callable] = None
_metadata_listener: Optional[Callable] = None
_permission_mode_listener: Optional[Callable] = None

_has_pending_action: bool = False
_current_state: SessionState = "idle"


def setSessionStateChangedListener(cb: Optional[Callable]) -> None:
    global _state_listener
    _state_listener = cb


def setSessionMetadataChangedListener(cb: Optional[Callable]) -> None:
    global _metadata_listener
    _metadata_listener = cb


def setPermissionModeChangedListener(cb: Optional[Callable]) -> None:
    """Register a listener for permission-mode changes from onChangeAppState."""
    global _permission_mode_listener
    _permission_mode_listener = cb


def getSessionState() -> SessionState:
    return _current_state


def notifySessionStateChanged(
    state: SessionState,
    details: Optional[RequiresActionDetails] = None,
) -> None:
    global _current_state, _has_pending_action
    _current_state = state
    if _state_listener:
        _state_listener(state, details)

    if state == "requires_action" and details:
        _has_pending_action = True
        if _metadata_listener:
            _metadata_listener({"pending_action": details})
    elif _has_pending_action:
        _has_pending_action = False
        if _metadata_listener:
            _metadata_listener({"pending_action": None})

    if state == "idle":
        if _metadata_listener:
            _metadata_listener({"task_summary": None})

    # Mirror to SDK event stream if configured
    try:
        from vivian_cli.utils.envUtils import isEnvTruthy
        if isEnvTruthy(os.environ.get("vivian_CODE_EMIT_SESSION_STATE_EVENTS")):
            from vivian_cli.utils.sdkEventQueue import enqueueSdkEvent
            enqueueSdkEvent({"type": "system", "subtype": "session_state_changed", "state": state})
    except Exception:
        pass


def notifySessionMetadataChanged(metadata: SessionExternalMetadata) -> None:
    if _metadata_listener:
        _metadata_listener(metadata)


def notifyPermissionModeChanged(mode: Any) -> None:
    """Fired by onChangeAppState when toolPermissionContext.mode changes."""
    if _permission_mode_listener:
        _permission_mode_listener(mode)


import os
