"""Shared task-stop logic mirroring src/tasks/stopTask.ts."""

from __future__ import annotations

from dataclasses import is_dataclass, replace
from typing import Any, Callable

from ..utils.sdkEventQueue import emitTaskTerminatedSdk
from .LocalShellTask.guards import isLocalShellTask


class StopTaskError(Exception):
    def __init__(self, message: str, code: str) -> None:
        super().__init__(message)
        self.code = code


def _task_field(task: Any, *names: str, default: Any = None) -> Any:
    if isinstance(task, dict):
        for name in names:
            if name in task:
                return task[name]
        return default
    for name in names:
        if hasattr(task, name):
            return getattr(task, name)
    return default


def _set_notified(task: Any) -> Any:
    if isinstance(task, dict):
        updated = dict(task)
        updated["notified"] = True
        return updated
    if is_dataclass(task):
        return replace(task, notified=True)
    setattr(task, "notified", True)
    return task


async def stopTask(taskId: str, context: dict[str, Callable[..., Any]]) -> dict[str, Any]:
    from . import getTaskByType

    getAppState = context["getAppState"]
    setAppState = context["setAppState"]
    app_state = getAppState()
    tasks = app_state.get("tasks", {}) if isinstance(app_state, dict) else getattr(app_state, "tasks", {})
    task = tasks.get(taskId)

    if task is None:
        raise StopTaskError(f"No task found with ID: {taskId}", "not_found")

    status = _task_field(task, "status")
    if status != "running":
        raise StopTaskError(f"Task {taskId} is not running (status: {status})", "not_running")

    task_type = _task_field(task, "type")
    task_impl = getTaskByType(task_type)
    if task_impl is None:
        raise StopTaskError(f"Unsupported task type: {task_type}", "unsupported_type")

    await task_impl.kill(taskId, setAppState)

    if isLocalShellTask(task):
        suppressed = False

        def _mark(prev: Any) -> Any:
            nonlocal suppressed
            prev_tasks = prev.get("tasks", {}) if isinstance(prev, dict) else getattr(prev, "tasks", {})
            prev_task = prev_tasks.get(taskId)
            if prev_task is None or _task_field(prev_task, "notified", default=False):
                return prev
            suppressed = True
            updated_tasks = dict(prev_tasks)
            updated_tasks[taskId] = _set_notified(prev_task)
            if isinstance(prev, dict):
                next_state = dict(prev)
                next_state["tasks"] = updated_tasks
                return next_state
            setattr(prev, "tasks", updated_tasks)
            return prev

        setAppState(_mark)
        if suppressed:
            emitTaskTerminatedSdk(
                taskId,
                "stopped",
                {
                    "toolUseId": _task_field(task, "tool_use_id", "toolUseId"),
                    "summary": _task_field(task, "description", default=""),
                },
            )

    command = _task_field(task, "command", default=None)
    if command is None:
        command = _task_field(task, "description", default=None)

    return {"taskId": taskId, "taskType": task_type, "command": command}