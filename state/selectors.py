"""Selectors for deriving computed state — mirrors src/state/selectors.ts."""

from __future__ import annotations

from typing import Any, Optional

from ..tasks.InProcessTeammateTask.types import isInProcessTeammateTask


# ---------------------------------------------------------------------------
# getViewedTeammateTask
# ---------------------------------------------------------------------------

def _get_field(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def getViewedTeammateTask(
    appState: dict,
) -> Optional[Any]:
    """Get the currently viewed teammate task, if any.

    Returns undefined if:
    - No teammate is being viewed (viewingAgentTaskId is undefined)
    - The task ID doesn't exist in tasks
    - The task is not an in-process teammate task
    """
    viewingAgentTaskId = _get_field(appState, "viewingAgentTaskId")
    tasks = _get_field(appState, "tasks", {})

    # Not viewing any teammate
    if not viewingAgentTaskId:
        return None

    # Look up the task
    task = tasks.get(viewingAgentTaskId) if isinstance(tasks, dict) else None
    if not task:
        return None

    # Verify it's an in-process teammate task
    if not isInProcessTeammateTask(task):
        return None

    return task


# ---------------------------------------------------------------------------
# ActiveAgentForInput
# ---------------------------------------------------------------------------

# Discriminated union type aliases
# {type: 'leader'} | {type: 'viewed', task: ...} | {type: 'named_agent', task: ...}
ActiveAgentForInput = dict


def getActiveAgentForInput(appState: dict) -> ActiveAgentForInput:
    """Determine where user input should be routed.

    Returns:
    - {type: 'leader'} when not viewing a teammate
    - {type: 'viewed', task: ...} when viewing an agent
    - {type: 'named_agent', task: ...} when viewing a local_agent task
    """
    viewedTask = getViewedTeammateTask(appState)
    if viewedTask:
        return {"type": "viewed", "task": viewedTask}

    viewingAgentTaskId = _get_field(appState, "viewingAgentTaskId")
    if viewingAgentTaskId:
        tasks = _get_field(appState, "tasks", {})
        task = tasks.get(viewingAgentTaskId) if isinstance(tasks, dict) else None
        if _get_field(task, "type") == "local_agent":
            return {"type": "named_agent", "task": task}

    return {"type": "leader"}

