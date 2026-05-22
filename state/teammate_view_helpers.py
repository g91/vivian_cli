"""Teammate view helpers — mirrors src/state/teammateViewHelpers.ts."""
from __future__ import annotations

from typing import Callable


def enter_teammate_view(task_id: str, set_app_state: Callable) -> None:
    """Set the viewed teammate task and retain it."""
    def updater(prev: dict) -> dict:
        state = dict(prev)
        state["viewingAgentTaskId"] = task_id
        # Mark task as retained
        tasks = dict(state.get("tasks", {}))
        if task_id in tasks:
            task = dict(tasks[task_id])
            task["retain"] = True
            tasks[task_id] = task
            state["tasks"] = tasks
        return state
    set_app_state(updater)


def exit_teammate_view(task_id: str, set_app_state: Callable) -> None:
    """Clear the viewed teammate and release the task to stub form."""
    def updater(prev: dict) -> dict:
        state = dict(prev)
        if state.get("viewingAgentTaskId") == task_id:
            state["viewingAgentTaskId"] = None
        tasks = dict(state.get("tasks", {}))
        if task_id in tasks:
            task = dict(tasks[task_id])
            task.pop("retain", None)
            tasks[task_id] = task
            state["tasks"] = tasks
        return state
    set_app_state(updater)
