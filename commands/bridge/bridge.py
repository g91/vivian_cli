"""bridge command — mirrors src/commands/bridge/bridge.tsx.

Manage the bridge connection for remote control / headless operation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ...bridge.bridgeStatusUtil import getBridgeStatus
from ...bridge.types import REMOTE_CONTROL_DISCONNECTED_MSG

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


def bridgeStatus() -> str:
    """Get bridge status summary."""
    return "Remote Control disconnected. Use /bridge connect to start."


async def call(args: str, context: CommandContext) -> TextResult:
    """Manage bridge connection."""
    from ...types.command import TextResult
    parts = args.strip().split(maxsplit=1) if args.strip() else []
    action = parts[0].lower() if parts else ""

    if not action or action == "status":
        return TextResult(_get_bridge_status(context))

    if action == "connect":
        return TextResult(await _connect_bridge(context))

    if action == "disconnect":
        return TextResult(_disconnect_bridge(context))

    if action == "reconnect":
        return TextResult(_reconnect_bridge(context))

    return TextResult("Usage: /bridge [status|connect|disconnect|reconnect]")


def _get_bridge_status(context: CommandContext) -> str:
    state = _get_app_state(context)
    enabled = bool(state.get("replBridgeEnabled", False))
    connected = bool(state.get("replBridgeConnected", False))
    session_active = bool(state.get("replBridgeSessionActive", False))
    reconnecting = bool(state.get("replBridgeReconnecting", False))
    error = state.get("replBridgeError")

    if not any((enabled, connected, session_active, reconnecting, error)):
        return bridgeStatus()

    summary = getBridgeStatus(error, connected, session_active, reconnecting)["label"]
    lines = [summary]

    environment_id = state.get("replBridgeEnvironmentId")
    session_id = state.get("replBridgeSessionId")
    connect_url = state.get("replBridgeConnectUrl")
    session_url = state.get("replBridgeSessionUrl")

    if environment_id:
        lines.append(f"Environment: {environment_id}")
    if session_id:
        lines.append(f"Session: {session_id}")
    if session_url:
        lines.append(f"Session URL: {session_url}")
    elif connect_url:
        lines.append(f"Connect URL: {connect_url}")
    if error:
        lines.append(f"Error: {error}")

    return "\n".join(lines)


async def _connect_bridge(context: CommandContext) -> str:
    try:
        from ...bridge.bridgeEnabled import checkBridgeMinVersion, getBridgeDisabledReason

        version_error = checkBridgeMinVersion()
        if version_error:
            return version_error

        disabled_reason = await getBridgeDisabledReason()
        if disabled_reason:
            return disabled_reason
    except Exception:
        pass

    _update_app_state(
        context,
        {
            "replBridgeEnabled": True,
            "replBridgeExplicit": True,
            "replBridgeOutboundOnly": False,
            "replBridgeReconnecting": False,
            "replBridgeError": None,
        },
    )
    return "Remote Control connecting..."


def _disconnect_bridge(context: CommandContext) -> str:
    _update_app_state(
        context,
        {
            "replBridgeEnabled": False,
            "replBridgeExplicit": False,
            "replBridgeConnected": False,
            "replBridgeSessionActive": False,
            "replBridgeReconnecting": False,
            "replBridgeConnectUrl": None,
            "replBridgeSessionUrl": None,
            "replBridgeEnvironmentId": None,
            "replBridgeSessionId": None,
            "replBridgeError": None,
        },
    )
    return REMOTE_CONTROL_DISCONNECTED_MSG


def _reconnect_bridge(context: CommandContext) -> str:
    state = _get_app_state(context)
    if not any((state.get("replBridgeEnabled"), state.get("replBridgeConnected"), state.get("replBridgeSessionActive"))):
        _update_app_state(
            context,
            {
                "replBridgeEnabled": True,
                "replBridgeExplicit": True,
                "replBridgeOutboundOnly": False,
            },
        )
    _update_app_state(
        context,
        {
            "replBridgeReconnecting": True,
            "replBridgeError": None,
        },
    )
    return "Remote Control reconnecting..."


def _get_app_state(context: Any) -> dict[str, Any]:
    try:
        state_store = getattr(context, "state_store", None)
        if state_store is not None and hasattr(state_store, "get_state"):
            state = state_store.get_state()
            if isinstance(state, dict):
                return state
    except Exception:
        pass

    try:
        if hasattr(context, "get_app_state"):
            state = context.get_app_state()
            if isinstance(state, dict):
                return state
        if hasattr(context, "getAppState"):
            state = context.getAppState()
            if isinstance(state, dict):
                return state
    except Exception:
        pass

    app_state = getattr(context, "app_state", None)
    if isinstance(app_state, dict):
        return app_state
    if app_state is not None:
        return getattr(app_state, "__dict__", {}) or {}
    return {}


def _update_app_state(context: Any, changes: dict[str, Any]) -> None:
    state_store = getattr(context, "state_store", None)
    if state_store is not None and hasattr(state_store, "set_state"):
        try:
            state_store.set_state(lambda prev: {**(prev or {}), **changes})
            return
        except Exception:
            pass

    for setter_name in ("set_app_state", "setAppState"):
        setter = getattr(context, setter_name, None)
        if callable(setter):
            try:
                setter(lambda prev: {**(prev or {}), **changes})
                return
            except Exception:
                pass

    app_state = getattr(context, "app_state", None)
    if isinstance(app_state, dict):
        app_state.update(changes)
        return
    if app_state is not None:
        for key, value in changes.items():
            try:
                setattr(app_state, key, value)
            except Exception:
                pass


bridge_status = bridgeStatus
