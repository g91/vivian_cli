"""
Port of src/utils/sessionRestore.ts
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
import os
import os.path
import json
import asyncio
import hashlib
import uuid

from ..bootstrap.state import clearSystemPromptSectionState, getMainLoopModelOverride, getSessionId, setMainLoopModelOverride, setMainThreadAgentType, setOriginalCwd
from ..tools.TodoWriteTool.constants import TODO_WRITE_TOOL_NAME
from .commitAttribution import attributionRestoreStateFromLog, restoreAttributionStateFromSnapshots
from .cwd import get_cwd, set_cwd
from .fileHistory import fileHistoryRestoreStateFromLog
from .model.model import parseUserSpecifiedModel
from .plans import getPlansDirectory
from .tasks import isTodoV2Enabled
from ..tools.AgentTool.loadAgentsDir import loadAgentsDir


ResumeResult = Dict[str, Any]
ProcessedResume = Dict[str, Any]
CoordinatorModeApi = Dict[str, Any]
ResumeLoadResult = Dict[str, Any]


_restored_worktree_session: Optional[Dict[str, Any]] = None


def _clear_resume_caches() -> None:
    clearSystemPromptSectionState()
    cache_clear = getattr(getPlansDirectory, 'cache_clear', None)
    if callable(cache_clear):
        cache_clear()


def extractTodosFromTranscript(messages):
    """Scan the transcript for the last TodoWrite tool_use block and return its todos."""
    if not isinstance(messages, list):
        return []
    for message in reversed(messages):
        if not isinstance(message, dict) or message.get('type') != 'assistant':
            continue
        payload = message.get('message')
        content = payload.get('content') if isinstance(payload, dict) else message.get('content')
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get('type') != 'tool_use' or block.get('name') != TODO_WRITE_TOOL_NAME:
                continue
            input_data = block.get('input')
            if not isinstance(input_data, dict):
                return []
            todos = input_data.get('todos')
            if not isinstance(todos, list):
                return []
            return [todo for todo in todos if isinstance(todo, dict)]
    return []


def restoreSessionStateFromLog(result, setAppState):
    """Restore session state (file history, attribution, todos) from log on resume."""
    if not isinstance(result, dict) or not callable(setAppState):
        return None

    file_history_snapshots = result.get('fileHistorySnapshots') or []
    if file_history_snapshots:
        fileHistoryRestoreStateFromLog(
            file_history_snapshots,
            lambda new_state: setAppState(lambda prev: {**prev, 'fileHistory': new_state}),
        )

    attribution_snapshots = result.get('attributionSnapshots') or []
    if attribution_snapshots:
        attributionRestoreStateFromLog(
            attribution_snapshots,
            lambda new_state: setAppState(lambda prev: {**prev, 'attribution': new_state}),
        )

    if not isTodoV2Enabled() and result.get('messages'):
        todos = extractTodosFromTranscript(result.get('messages'))
        if todos:
            agent_id = getSessionId()
            setAppState(
                lambda prev: {
                    **prev,
                    'todos': {
                        **(prev.get('todos') or {}),
                        agent_id: todos,
                    },
                }
            )
    return None


def computeRestoredAttributionState(result):
    """Compute restored attribution state from log snapshots."""
    if not isinstance(result, dict):
        return None
    attribution_snapshots = result.get('attributionSnapshots') or []
    if not attribution_snapshots:
        return None
    return restoreAttributionStateFromSnapshots(attribution_snapshots)


def computeStandaloneAgentContext(agentName, agentColor):
    """Compute standalone agent context (name/color) for session resume."""
    if not agentName and not agentColor:
        return None
    return {
        'name': agentName or '',
        'color': None if agentColor == 'default' else agentColor,
    }


def restoreAgentFromSession(agentSetting, currentAgentDefinition, agentDefinitions):
    """Restore agent setting from a resumed session."""
    if currentAgentDefinition is not None:
        return {
            'agentDefinition': currentAgentDefinition,
            'agentType': None,
        }

    if not agentSetting:
        setMainThreadAgentType(None)
        return {
            'agentDefinition': None,
            'agentType': None,
        }

    active_agents = []
    if isinstance(agentDefinitions, dict):
        active_agents = agentDefinitions.get('activeAgents') or []
    else:
        active_agents = getattr(agentDefinitions, 'activeAgents', []) or []

    resumed_agent = None
    for agent in active_agents:
        agent_type = agent.get('agentType') if isinstance(agent, dict) else getattr(agent, 'agentType', None)
        if agent_type == agentSetting:
            resumed_agent = agent
            break

    if resumed_agent is None:
        setMainThreadAgentType(None)
        return {
            'agentDefinition': None,
            'agentType': None,
        }

    resumed_agent_type = resumed_agent.get('agentType') if isinstance(resumed_agent, dict) else getattr(resumed_agent, 'agentType', None)
    setMainThreadAgentType(resumed_agent_type)

    resumed_model = resumed_agent.get('model') if isinstance(resumed_agent, dict) else getattr(resumed_agent, 'model', None)
    if not getMainLoopModelOverride() and resumed_model and resumed_model != 'inherit':
        setMainLoopModelOverride(parseUserSpecifiedModel(resumed_model))

    return {
        'agentDefinition': resumed_agent,
        'agentType': resumed_agent_type,
    }


async def refreshAgentDefinitionsForModeSwitch(modeWasSwitched, currentCwd, cliAgents, currentAgentDefinitions):
    """Refresh agent definitions after a coordinator/normal mode switch."""
    if not modeWasSwitched:
        return currentAgentDefinitions

    fresh_agents = loadAgentsDir(currentCwd)
    merged_all_agents = [*fresh_agents, *(cliAgents or [])]
    return {
        'allAgents': merged_all_agents,
        'activeAgents': merged_all_agents,
    }


def restoreWorktreeForResume(worktreeSession):
    """Restore the worktree working directory on resume. The transcript records"""
    global _restored_worktree_session

    if _restored_worktree_session:
        return None
    if not isinstance(worktreeSession, dict):
        return None

    worktree_path = worktreeSession.get('worktreePath')
    if not isinstance(worktree_path, str) or not worktree_path:
        return None

    try:
        os.chdir(worktree_path)
    except Exception:
        _restored_worktree_session = None
        return None

    set_cwd(worktree_path)
    setOriginalCwd(get_cwd())
    _restored_worktree_session = dict(worktreeSession)
    _clear_resume_caches()
    return None


def exitRestoredWorktree():
    """Undo restoreWorktreeForResume before a mid-session /resume switches to"""
    global _restored_worktree_session

    current = _restored_worktree_session
    if not current:
        return None

    _restored_worktree_session = None
    _clear_resume_caches()

    original_cwd = current.get('originalCwd')
    if not isinstance(original_cwd, str) or not original_cwd:
        return None
    try:
        os.chdir(original_cwd)
    except Exception:
        return None
    set_cwd(original_cwd)
    setOriginalCwd(get_cwd())
    return None


async def processResumedConversation(result, context, opts=None):
    """Process a loaded conversation for resume/continue."""
    result = result if isinstance(result, dict) else {}
    context = context if isinstance(context, dict) else {}
    opts = opts if isinstance(opts, dict) else {}

    fork_session = bool(opts.get('forkSession', False))
    include_attribution = bool(opts.get('includeAttribution', False))
    current_cwd = context.get('currentCwd') or get_cwd()
    cli_agents = context.get('cliAgents') or []
    initial_state = dict(context.get('initialState') or {})

    def _update_initial_state(updater):
        nonlocal initial_state
        try:
            next_state = updater(initial_state)
        except Exception:
            return None
        if isinstance(next_state, dict):
            initial_state = next_state
        return None

    current_agent_definitions = context.get('agentDefinitions')
    if not isinstance(current_agent_definitions, dict):
        current_agent_definitions = initial_state.get('agentDefinitions') or {}
    if not isinstance(current_agent_definitions, dict):
        current_agent_definitions = {}

    if not current_agent_definitions.get('activeAgents'):
        loaded_agents = loadAgentsDir(current_cwd)
        merged_agents = [*loaded_agents, *(cli_agents or [])]
        current_agent_definitions = {
            'allAgents': merged_agents,
            'activeAgents': merged_agents,
        }

    restoreSessionStateFromLog(result, _update_initial_state)

    if not fork_session:
        exitRestoredWorktree()
        restoreWorktreeForResume(result.get('worktreeSession'))

    restored_agent = restoreAgentFromSession(
        result.get('agentSetting'),
        context.get('mainThreadAgentDefinition'),
        current_agent_definitions,
    )
    refreshed_agent_defs = await refreshAgentDefinitionsForModeSwitch(
        False,
        current_cwd,
        cli_agents,
        current_agent_definitions,
    )

    standalone_agent_context = computeStandaloneAgentContext(
        result.get('agentName'),
        result.get('agentColor'),
    )
    restored_attribution = computeRestoredAttributionState(result) if include_attribution else None

    initial_state = {
        **initial_state,
        'agentDefinitions': refreshed_agent_defs,
    }
    if restored_attribution is not None:
        initial_state['attribution'] = restored_attribution
    if standalone_agent_context is not None:
        initial_state['standaloneAgentContext'] = standalone_agent_context
    resumed_agent_type = restored_agent.get('agentType') if isinstance(restored_agent, dict) else None
    if resumed_agent_type:
        initial_state['agent'] = resumed_agent_type

    return {
        'messages': result.get('messages') or [],
        'fileHistorySnapshots': result.get('fileHistorySnapshots'),
        'contentReplacements': result.get('contentReplacements'),
        'agentName': result.get('agentName'),
        'agentColor': None if result.get('agentColor') == 'default' else result.get('agentColor'),
        'restoredAgentDef': restored_agent.get('agentDefinition') if isinstance(restored_agent, dict) else None,
        'initialState': initial_state,
    }

