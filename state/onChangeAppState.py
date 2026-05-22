"""App state change handler — mirrors src/state/onChangeAppState.ts."""
from __future__ import annotations

import os
import logging
from typing import Callable

log = logging.getLogger(__name__)


def externalMetadataToAppState(metadata: dict) -> Callable[[dict], dict]:
    """Inverse of the push below — restore on worker restart.

    Mirrors externalMetadataToAppState() from onChangeAppState.ts.
    """
    def apply(prev: dict) -> dict:
        new_state = dict(prev)
        if "permission_mode" in metadata and isinstance(metadata["permission_mode"], str):
            tool_ctx = dict(prev.get("toolPermissionContext", {}))
            tool_ctx["mode"] = _permission_mode_from_string(metadata["permission_mode"])
            new_state["toolPermissionContext"] = tool_ctx
        if "is_ultraplan_mode" in metadata and isinstance(metadata["is_ultraplan_mode"], bool):
            new_state["isUltraplanMode"] = metadata["is_ultraplan_mode"]
        return new_state
    return apply


def onChangeAppState(*, newState: dict, oldState: dict) -> None:
    """Called whenever app state changes.

    Mirrors onChangeAppState() from onChangeAppState.ts.
    Handles permission mode sync, model override, expandedView persistence, etc.
    """
    # toolPermissionContext.mode — sync to CCR/SDK
    prevMode = oldState.get("toolPermissionContext", {}).get("mode")
    newMode = newState.get("toolPermissionContext", {}).get("mode")
    if prevMode != newMode:
        prevExternal = _to_external_permission_mode(prevMode)
        newExternal = _to_external_permission_mode(newMode)
        if prevExternal != newExternal:
            isUltraplan = (
                True
                if (
                    newExternal == "plan"
                    and newState.get("isUltraplanMode")
                    and not oldState.get("isUltraplanMode")
                )
                else None
            )
            try:
                from ..utils.sessionState import notifySessionMetadataChanged

                notifySessionMetadataChanged({
                    "permission_mode": newExternal,
                    "is_ultraplan_mode": isUltraplan,
                })
            except Exception:
                pass
        try:
            from ..utils.sessionState import notifyPermissionModeChanged

            notifyPermissionModeChanged(newMode)
        except Exception:
            pass

    # mainLoopModel: remove from settings?
    if (
        newState.get("mainLoopModel") != oldState.get("mainLoopModel")
        and newState.get("mainLoopModel") is None
    ):
        try:
            from ..utils.settings.settings import updateSettingsForSource
            from ..bootstrap.state import setMainLoopModelOverride

            updateSettingsForSource("userSettings", {"model": None})
            setMainLoopModelOverride(None)
        except Exception:
            pass

    # mainLoopModel: add to settings?
    if (
        newState.get("mainLoopModel") != oldState.get("mainLoopModel")
        and newState.get("mainLoopModel") is not None
    ):
        try:
            from ..utils.settings.settings import updateSettingsForSource
            from ..bootstrap.state import setMainLoopModelOverride

            updateSettingsForSource("userSettings", {"model": newState["mainLoopModel"]})
            setMainLoopModelOverride(newState["mainLoopModel"])
        except Exception:
            pass

    # expandedView → persist as showExpandedTodos + showSpinnerTree
    if newState.get("expandedView") != oldState.get("expandedView"):
        showExpandedTodos = newState.get("expandedView") == "tasks"
        showSpinnerTree = newState.get("expandedView") == "teammates"
        try:
            from ..utils.config import get_global_config, save_global_config

            cfg = get_global_config()
            if (
                cfg.get("showExpandedTodos") != showExpandedTodos
                or cfg.get("showSpinnerTree") != showSpinnerTree
            ):
                save_global_config(lambda c: {**c, "showExpandedTodos": showExpandedTodos, "showSpinnerTree": showSpinnerTree})
        except Exception:
            pass

    # verbose
    if newState.get("verbose") != oldState.get("verbose"):
        try:
            from ..utils.config import get_global_config, save_global_config

            cfg = get_global_config()
            if cfg.get("verbose") != newState.get("verbose"):
                verbose = newState["verbose"]
                save_global_config(lambda c: {**c, "verbose": verbose})
        except Exception:
            pass

    # tungstenPanelVisible (ant-only)
    if os.environ.get("USER_TYPE") == "ant":
        if (
            newState.get("tungstenPanelVisible") != oldState.get("tungstenPanelVisible")
            and newState.get("tungstenPanelVisible") is not None
        ):
            try:
                from ..utils.config import get_global_config, save_global_config

                cfg = get_global_config()
                if cfg.get("tungstenPanelVisible") != newState.get("tungstenPanelVisible"):
                    v = newState["tungstenPanelVisible"]
                    save_global_config(lambda c: {**c, "tungstenPanelVisible": v})
            except Exception:
                pass

    # settings: clear auth-related caches
    if newState.get("settings") is not oldState.get("settings"):
        try:
            from ..utils.auth import (
                clearApiKeyHelperCache,
                clearAwsCredentialsCache,
                clearGcpCredentialsCache,
            )

            clearApiKeyHelperCache()
            clearAwsCredentialsCache()
            clearGcpCredentialsCache()

            if newState.get("settings", {}).get("env") != oldState.get("settings", {}).get("env"):
                from ..utils.managedEnv import applyConfigEnvironmentVariables

                applyConfigEnvironmentVariables()
        except Exception as error:
            try:
                from ..utils.log import logError

                logError(error)
            except Exception:
                log.error("onChangeAppState settings error: %s", error)


def _permission_mode_from_string(s: str) -> str:
    """Convert external permission mode string to internal."""
    try:
        from ..utils.permissions.PermissionMode import permissionModeFromString

        return permissionModeFromString(s)
    except Exception:
        return s


def _to_external_permission_mode(mode: str | None) -> str | None:
    """Convert internal permission mode to external."""
    if mode is None:
        return None
    try:
        from ..utils.permissions.PermissionMode import toExternalPermissionMode

        return toExternalPermissionMode(mode)
    except Exception:
        return mode
