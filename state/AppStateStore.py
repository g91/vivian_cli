"""AppState definition and defaults — mirrors src/state/AppStateStore.ts."""

from __future__ import annotations

from typing import Any

from .store import Store


# ---------------------------------------------------------------------------
# Type aliases (simplified Python equivalents of TS complex types)
# ---------------------------------------------------------------------------

CompletionBoundary = dict
SpeculationResult = dict
SpeculationState = dict

IDLE_SPECULATION_STATE: SpeculationState = {"status": "idle"}

FooterItem = str


# ---------------------------------------------------------------------------
# AppState
# ---------------------------------------------------------------------------

def _get_initial_settings() -> dict[str, Any]:
    try:
        from ..utils.settings.settings import getMergedSettings

        return getMergedSettings()
    except Exception:
        return {}


def _should_enable_prompt_suggestion() -> bool:
    try:
        from ..services.PromptSuggestion import shouldEnablePromptSuggestion

        return shouldEnablePromptSuggestion()
    except Exception:
        return False


def _should_enable_thinking_by_default() -> bool:
    try:
        from ..utils.thinking import shouldEnableThinkingByDefault

        return shouldEnableThinkingByDefault()
    except Exception:
        return False


def _create_empty_attribution_state() -> dict[str, Any]:
    try:
        from ..utils.commitAttribution import createEmptyAttributionState

        return createEmptyAttributionState()
    except Exception:
        return {"fileStates": {}, "promptCount": 0, "permissionPromptCount": 0, "escapeCount": 0}


def _get_empty_tool_permission_context() -> dict[str, Any]:
    return {
        "mode": "default",
        "isBypassPermissionsModeAvailable": False,
        "isAutoModeAvailable": False,
        "canAcceptEdits": False,
        "disableBypassPermissions": False,
        "additionalWorkingDirectories": [],
        "rules": [],
    }


def _get_initial_mode() -> str:
    try:
        from ..utils.teammate import is_teammate, is_plan_mode_required

        if is_teammate() and is_plan_mode_required():
            return "plan"
    except Exception:
        pass
    return "default"


def get_default_app_state() -> dict[str, Any]:
    """Return the default AppState — mirrors getDefaultAppState() from AppStateStore.ts."""
    tool_permission_context = _get_empty_tool_permission_context()
    tool_permission_context["mode"] = _get_initial_mode()

    return {
        "settings": _get_initial_settings(),
        "verbose": False,
        "mainLoopModel": None,
        "mainLoopModelForSession": None,
        "statusLineText": None,
        "expandedView": "none",
        "isBriefOnly": False,
        "showTeammateMessagePreview": False,
        "selectedIPAgentIndex": -1,
        "coordinatorTaskIndex": -1,
        "viewSelectionMode": "none",
        "footerSelection": None,
        "toolPermissionContext": tool_permission_context,
        "spinnerTip": None,
        "agent": None,
        "kairosEnabled": False,
        "remoteSessionUrl": None,
        "remoteConnectionStatus": "connecting",
        "remoteBackgroundTaskCount": 0,
        "replBridgeEnabled": False,
        "replBridgeExplicit": False,
        "replBridgeOutboundOnly": False,
        "replBridgeConnected": False,
        "replBridgeSessionActive": False,
        "replBridgeReconnecting": False,
        "replBridgeConnectUrl": None,
        "replBridgeSessionUrl": None,
        "replBridgeEnvironmentId": None,
        "replBridgeSessionId": None,
        "replBridgeError": None,
        "replBridgeInitialName": None,
        "showRemoteCallout": False,
        "tasks": {},
        "agentNameRegistry": {},
        "foregroundedTaskId": None,
        "viewingAgentTaskId": None,
        "companionReaction": None,
        "companionPetAt": None,
        "mcp": {
            "clients": [],
            "tools": [],
            "commands": [],
            "resources": {},
            "pluginReconnectKey": 0,
        },
        "plugins": {
            "enabled": [],
            "disabled": [],
            "commands": [],
            "errors": [],
            "installationStatus": {"marketplaces": [], "plugins": []},
            "needsRefresh": False,
        },
        "agentDefinitions": {"activeAgents": [], "allAgents": []},
        "fileHistory": {"snapshots": [], "trackedFiles": set(), "snapshotSequence": 0},
        "attribution": _create_empty_attribution_state(),
        "todos": {},
        "remoteAgentTaskSuggestions": [],
        "notifications": {"current": None, "queue": []},
        "elicitation": {"queue": []},
        "thinkingEnabled": _should_enable_thinking_by_default(),
        "promptSuggestionEnabled": _should_enable_prompt_suggestion(),
        "sessionHooks": {},
        "tungstenActiveSession": None,
        "tungstenLastCapturedTime": None,
        "tungstenLastCommand": None,
        "tungstenPanelVisible": None,
        "tungstenPanelAutoHidden": None,
        "bagelActive": None,
        "bagelUrl": None,
        "bagelPanelVisible": None,
        "computerUseMcpState": None,
        "replContext": None,
        "teamContext": None,
        "standaloneAgentContext": None,
        "inbox": {"messages": []},
        "workerSandboxPermissions": {"queue": [], "selectedIndex": 0},
        "pendingWorkerRequest": None,
        "pendingSandboxRequest": None,
        "promptSuggestion": {
            "text": None,
            "promptId": None,
            "shownAt": 0,
            "acceptedAt": 0,
            "generationRequestId": None,
        },
        "speculation": IDLE_SPECULATION_STATE,
        "speculationSessionTimeSavedMs": 0,
        "skillImprovement": {"suggestion": None},
        "authVersion": 0,
        "initialMessage": None,
        "pendingPlanVerification": None,
        "denialTracking": None,
        "activeOverlays": set(),
        "fastMode": False,
        "advisorModel": None,
        "effortValue": None,
        "ultraplanLaunching": None,
        "ultraplanSessionUrl": None,
        "ultraplanPendingChoice": None,
        "ultraplanLaunchPending": None,
        "isUltraplanMode": None,
        "replBridgePermissionCallbacks": None,
        "channelPermissionCallbacks": None,
    }


def getDefaultAppState() -> dict[str, Any]:
    return get_default_app_state()


# ---------------------------------------------------------------------------
# AppStateStore type alias
# ---------------------------------------------------------------------------

AppState = dict  # Python alias; actual state is a plain dict
AppStateStore = Store  # Store[AppState]
