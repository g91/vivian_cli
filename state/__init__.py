"""State package — mirrors src/state/."""
from .store import Store, create_store, createStore, StateStore
from .AppStateStore import (
    AppState, AppStateStore, get_default_app_state, getDefaultAppState,
    IDLE_SPECULATION_STATE, CompletionBoundary, SpeculationResult, SpeculationState,
)
from .selectors import getViewedTeammateTask, getActiveAgentForInput, ActiveAgentForInput
from .onChangeAppState import externalMetadataToAppState, onChangeAppState
from .teammateViewHelpers import enterTeammateView, exitTeammateView, stopOrDismissAgent

# Snake-case aliases for backwards compat
get_viewed_teammate_task = getViewedTeammateTask
get_active_agent_for_input = getActiveAgentForInput
external_metadata_to_app_state = externalMetadataToAppState
on_change_app_state = lambda new_state, old_state: onChangeAppState(newState=new_state, oldState=old_state)
enter_teammate_view = enterTeammateView
exit_teammate_view = exitTeammateView
stop_or_dismiss_agent = stopOrDismissAgent

__all__ = [
    "Store", "create_store", "createStore", "StateStore",
    "AppState", "AppStateStore", "get_default_app_state", "getDefaultAppState",
    "IDLE_SPECULATION_STATE", "CompletionBoundary", "SpeculationResult", "SpeculationState",
    "getViewedTeammateTask", "getActiveAgentForInput", "ActiveAgentForInput",
    "externalMetadataToAppState", "onChangeAppState",
    "enterTeammateView", "exitTeammateView", "stopOrDismissAgent",
    # snake_case aliases
    "get_viewed_teammate_task", "get_active_agent_for_input",
    "external_metadata_to_app_state", "on_change_app_state",
    "enter_teammate_view", "exit_teammate_view", "stop_or_dismiss_agent",
]

