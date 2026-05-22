"""
Port of src/utils/inProcessTeammateHelpers.ts
"""
from __future__ import annotations

from typing import Any

from ..tasks.InProcessTeammateTask.types import isInProcessTeammateTask
from .json import parse_json
from .task.framework import updateTaskState


SetAppState = Any


def findInProcessTeammateTaskId(agentName, appState):
    """Find the task ID for an in-process teammate by agent name.

@param agentName - The agent name (e.g., "researcher")
@param appState - Current AppState
@returns Task ID if found, undefined otherwise"""
    tasks = appState.get('tasks', {}) if isinstance(appState, dict) else getattr(appState, 'tasks', {})
    for task in (tasks or {}).values():
        if not isInProcessTeammateTask(task):
            continue
        identity = task.get('identity', {}) if isinstance(task, dict) else getattr(task, 'identity', None)
        teammate_name = identity.get('agentName') if isinstance(identity, dict) else getattr(identity, 'agentName', None)
        if teammate_name == agentName:
            return task.get('id') if isinstance(task, dict) else getattr(task, 'id', None)
    return None


def setAwaitingPlanApproval(taskId, setAppState, awaiting):
    """Set awaitingPlanApproval state for an in-process teammate.

@param taskId - Task ID of the in-process teammate
@param setAppState - AppState setter
@param awaiting - Whether teammate is awaiting plan approval"""
    updateTaskState(
        taskId,
        setAppState,
        lambda task: {
            **task,
            'awaitingPlanApproval': awaiting,
        }
        if isinstance(task, dict)
        else _replace_object(task, awaiting),
    )
    return None


def handlePlanApprovalResponse(taskId, _response, setAppState):
    """Handle plan approval response for an in-process teammate.
Called by the message callback when a plan_approval_response arrives.

This resets awaitingPlanApproval to false. The permissionMode from the
response is handled separately by the agent loop (Task #11).

@param taskId - Task ID of the in-process teammate
@param _response - The plan approval response message (for future use)
@param setAppState - AppState setter"""
    setAwaitingPlanApproval(taskId, setAppState, False)
    return None


def isPermissionRelatedResponse(messageText):
    """Check if a message is a permission-related response.
Used by in-process teammate message handlers to detect and process
permission responses from the team leader.

Handles both tool permissions and sandbox (network host) permissions.

@param messageText - The raw message text to check
@returns true if the message is a permission response"""
    parsed = parse_json(messageText, None)
    if not isinstance(parsed, dict):
        return False
    return parsed.get('type') in {'permission_response', 'sandbox_permission_response'}


def _replace_object(task: Any, awaiting: bool) -> Any:
    try:
        from copy import copy

        cloned = copy(task)
        setattr(cloned, 'awaitingPlanApproval', awaiting)
        return cloned
    except Exception:
        return task


find_in_process_teammate_task_id = findInProcessTeammateTaskId
set_awaiting_plan_approval = setAwaitingPlanApproval
handle_plan_approval_response = handlePlanApprovalResponse
is_permission_related_response = isPermissionRelatedResponse

