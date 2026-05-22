"""Port of src/utils/task/framework.ts."""

from __future__ import annotations

import time
from copy import copy
from dataclasses import is_dataclass, replace
from typing import Any, Dict

from ...Task import isTerminalTaskStatus
from ...utils.messageQueueManager import enqueuePendingNotification
from ...utils.sdkEventQueue import enqueueSdkEvent


TaskAttachment = Dict[str, Any]
SetAppState = Any


POLL_INTERVAL_MS = 1000
STOPPED_DISPLAY_MS = 3000
PANEL_GRACE_MS = 30000


def _get_tasks(state: Any) -> dict[str, Any]:
    return state.get("tasks", {}) if isinstance(state, dict) else getattr(state, "tasks", {})


def _replace_state_tasks(state: Any, tasks: dict[str, Any]) -> Any:
    if isinstance(state, dict):
        next_state = dict(state)
        next_state["tasks"] = tasks
        return next_state
    next_state = copy(state)
    setattr(next_state, "tasks", tasks)
    return next_state


def _replace_task(task: Any, **updates: Any) -> Any:
    if isinstance(task, dict):
        merged = dict(task)
        merged.update(updates)
        return merged
    if is_dataclass(task):
        return replace(task, **updates)
    cloned = copy(task)
    for key, value in updates.items():
        setattr(cloned, key, value)
    return cloned


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


def _get_disk_output_helpers():
    try:
        from . import diskOutput
    except Exception:
        return None, None
    return getattr(diskOutput, "getTaskOutputDelta", None), getattr(diskOutput, "getTaskOutputPath", None)


def updateTaskState(taskId, setAppState, updater=None):
    """Update a task's state in AppState."""

    def _update(prev: Any) -> Any:
        tasks = _get_tasks(prev)
        task = tasks.get(taskId)
        if task is None:
            return prev
        updated = updater(task)
        if updated is task:
            return prev
        next_tasks = dict(tasks)
        next_tasks[taskId] = updated
        return _replace_state_tasks(prev, next_tasks)

    setAppState(_update)


def registerTask(task, setAppState):
    """Register a new task in AppState."""
    is_replacement = False

    def _register(prev: Any) -> Any:
        nonlocal is_replacement
        tasks = _get_tasks(prev)
        task_id = _task_field(task, "id")
        existing = tasks.get(task_id)
        is_replacement = existing is not None
        merged = task
        if existing is not None and _task_field(existing, "retain", default=None) is not None:
            merged = _replace_task(
                task,
                retain=_task_field(existing, "retain", default=False),
                start_time=_task_field(existing, "start_time", "startTime", default=_task_field(task, "start_time", "startTime")),
                messages=_task_field(existing, "messages"),
                disk_loaded=_task_field(existing, "disk_loaded", "diskLoaded", default=False),
                pending_messages=_task_field(existing, "pending_messages", "pendingMessages", default=[]),
            )
        next_tasks = dict(tasks)
        next_tasks[task_id] = merged
        return _replace_state_tasks(prev, next_tasks)

    setAppState(_register)
    if is_replacement:
        return
    enqueueSdkEvent(
        {
            "type": "system",
            "subtype": "task_started",
            "task_id": _task_field(task, "id"),
            "tool_use_id": _task_field(task, "tool_use_id", "toolUseId"),
            "description": _task_field(task, "description", default=""),
            "task_type": _task_field(task, "type", default=""),
            "workflow_name": _task_field(task, "workflow_name", "workflowName"),
            "prompt": _task_field(task, "prompt"),
        }
    )


def evictTerminalTask(taskId, setAppState):
    """Eagerly evict a terminal task from AppState."""

    def _evict(prev: Any) -> Any:
        tasks = _get_tasks(prev)
        task = tasks.get(taskId)
        if task is None:
            return prev
        if not isTerminalTaskStatus(_task_field(task, "status", default="pending")):
            return prev
        if not _task_field(task, "notified", default=False):
            return prev
        evict_after = _task_field(task, "evict_after", "evictAfter")
        if _task_field(task, "retain", default=None) is not None and (evict_after if evict_after is not None else float("inf")) > time.time() * 1000:
            return prev
        next_tasks = dict(tasks)
        next_tasks.pop(taskId, None)
        return _replace_state_tasks(prev, next_tasks)

    setAppState(_evict)


def getRunningTasks(state):
    """Get all running tasks."""
    return [task for task in _get_tasks(state).values() if _task_field(task, "status") == "running"]


async def generateTaskAttachments(state):
    """Generate attachments for tasks with new output or status changes."""
    attachments: list[TaskAttachment] = []
    updated_task_offsets: dict[str, int] = {}
    evicted_task_ids: list[str] = []

    for task_state in _get_tasks(state).values():
        if _task_field(task_state, "notified", default=False):
            status = _task_field(task_state, "status")
            if status in {"completed", "failed", "killed", "stopped"}:
                evicted_task_ids.append(_task_field(task_state, "id"))
                continue
            if status == "pending":
                continue

        if _task_field(task_state, "status") == "running":
            getTaskOutputDelta, _ = _get_disk_output_helpers()
            if getTaskOutputDelta is None:
                continue
            try:
                delta = await getTaskOutputDelta(
                    _task_field(task_state, "id"),
                    _task_field(task_state, "output_offset", "outputOffset", default=0),
                )
            except Exception:
                delta = None
            if isinstance(delta, dict) and delta.get("content"):
                updated_task_offsets[_task_field(task_state, "id")] = int(
                    delta.get(
                        "newOffset",
                        _task_field(task_state, "output_offset", "outputOffset", default=0),
                    )
                )

    return {
        "attachments": attachments,
        "updatedTaskOffsets": updated_task_offsets,
        "evictedTaskIds": evicted_task_ids,
    }


def applyTaskOffsetsAndEvictions(setAppState, updatedTaskOffsets, evictedTaskIds):
    """Apply the outputOffset patches and evictions from generateTaskAttachments."""
    if not updatedTaskOffsets and not evictedTaskIds:
        return

    def _apply(prev: Any) -> Any:
        tasks = dict(_get_tasks(prev))
        changed = False
        for task_id, new_offset in updatedTaskOffsets.items():
            fresh = tasks.get(task_id)
            if fresh is not None and _task_field(fresh, "status") == "running":
                tasks[task_id] = _replace_task(fresh, output_offset=new_offset)
                changed = True
        for task_id in evictedTaskIds:
            fresh = tasks.get(task_id)
            if fresh is None:
                continue
            if not isTerminalTaskStatus(_task_field(fresh, "status", default="pending")):
                continue
            if not _task_field(fresh, "notified", default=False):
                continue
            evict_after = _task_field(fresh, "evict_after", "evictAfter")
            if _task_field(fresh, "retain", default=None) is not None and (evict_after if evict_after is not None else float("inf")) > time.time() * 1000:
                continue
            del tasks[task_id]
            changed = True
        return _replace_state_tasks(prev, tasks) if changed else prev

    setAppState(_apply)


async def pollTasks(getAppState=None, setAppState=None):
    """Poll all running tasks and check for updates."""
    state = getAppState()
    generated = await generateTaskAttachments(state)
    applyTaskOffsetsAndEvictions(
        setAppState,
        generated["updatedTaskOffsets"],
        generated["evictedTaskIds"],
    )
    for attachment in generated["attachments"]:
        enqueueTaskNotification(attachment)


def enqueueTaskNotification(attachment):
    """Enqueue a task notification to the message queue."""
    status_text = getStatusText(attachment["status"])
    _, getTaskOutputPath = _get_disk_output_helpers()
    output_path = getTaskOutputPath(attachment["taskId"]) if getTaskOutputPath is not None else ""
    tool_use_id = attachment.get("toolUseId")
    tool_use_id_line = f"\n<tool_use_id>{tool_use_id}</tool_use_id>" if tool_use_id else ""
    message = (
        "<task_notification>\n"
        f"<task_id>{attachment['taskId']}</task_id>{tool_use_id_line}\n"
        f"<task_type>{attachment['taskType']}</task_type>\n"
        f"<output_file>{output_path}</output_file>\n"
        f"<status>{attachment['status']}</status>\n"
        f"<summary>Task \"{attachment['description']}\" {status_text}</summary>\n"
        "</task_notification>"
    )
    enqueuePendingNotification({"value": message, "mode": "task-notification"})


def getStatusText(status):
    """Get human-readable status text."""
    return {
        "completed": "completed successfully",
        "failed": "failed",
        "killed": "was stopped",
        "stopped": "was stopped",
        "running": "is running",
        "pending": "is pending",
    }.get(status, status)

