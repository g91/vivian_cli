"""Teammate view helpers — mirrors src/state/teammateViewHelpers.ts."""

from __future__ import annotations

import time
from dataclasses import fields, is_dataclass, replace
from typing import Any, Callable

from ..Task import isTerminalTaskStatus
from ..tasks.LocalAgentTask.LocalAgentTask import isLocalAgentTask

# Inline from framework.ts — keep in sync with PANEL_GRACE_MS
PANEL_GRACE_MS = 30_000


def _task_get(task: Any, field: str, default: Any = None) -> Any:
    if isinstance(task, dict):
        return task.get(field, default)
    return getattr(task, field, default)


def _task_replace(task: Any, **updates: Any) -> Any:
    if isinstance(task, dict):
        merged = dict(task)
        merged.update(updates)
        return merged
    if is_dataclass(task):
        normalized = dict(updates)
        if "diskLoaded" in normalized and "disk_loaded" not in normalized:
            normalized["disk_loaded"] = normalized.pop("diskLoaded")
        else:
            normalized.pop("diskLoaded", None)
        if "evictAfter" in normalized and "evict_after" not in normalized:
            normalized["evict_after"] = normalized.pop("evictAfter")
        else:
            normalized.pop("evictAfter", None)
        allowed = {field.name for field in fields(task)}
        return replace(task, **{key: value for key, value in normalized.items() if key in allowed})
    for key, value in updates.items():
        setattr(task, key, value)
    return task


def _log_event(name: str, data: dict) -> None:
    try:
        from ..services.analytics.index import log_event
        log_event(name, data)
    except Exception:
        pass


def _release(task: dict) -> dict:
    """Return the task released back to stub form.

    Mirrors release() from teammateViewHelpers.ts.
    """
    evict_after = (
        int(time.time() * 1000) + PANEL_GRACE_MS
        if isTerminalTaskStatus(_task_get(task, "status", ""))
        else None
    )
    return _task_replace(
        task,
        retain=False,
        messages=None,
        diskLoaded=False,
        evictAfter=evict_after,
        disk_loaded=False,
        evict_after=evict_after,
    )


def enterTeammateView(
    taskId: str,
    setAppState: Callable[[Callable[[dict], dict]], None],
) -> None:
    """Transition the UI to view a teammate's transcript.

    Mirrors enterTeammateView() from teammateViewHelpers.ts.
    """
    _log_event("tengu_transcript_view_enter", {})

    def updater(prev: dict) -> dict:
        task = prev.get("tasks", {}).get(taskId)
        prevId = prev.get("viewingAgentTaskId")
        prevTask = prev.get("tasks", {}).get(prevId) if prevId is not None else None
        switching = (
            prevId is not None
            and prevId != taskId
            and isLocalAgentTask(prevTask)
            and _task_get(prevTask, "retain")
        )
        needsRetain = isLocalAgentTask(task) and (
            not _task_get(task, "retain") or _task_get(task, "evictAfter", _task_get(task, "evict_after")) is not None
        )
        needsView = (
            prev.get("viewingAgentTaskId") != taskId
            or prev.get("viewSelectionMode") != "viewing-agent"
        )
        if not needsRetain and not needsView and not switching:
            return prev

        tasks = dict(prev.get("tasks", {}))
        if switching:
            tasks[prevId] = _release(prevTask)
        if needsRetain:
            tasks[taskId] = _task_replace(task, retain=True, evictAfter=None, evict_after=None)

        return {
            **prev,
            "viewingAgentTaskId": taskId,
            "viewSelectionMode": "viewing-agent",
            "tasks": tasks,
        }

    setAppState(updater)


def exitTeammateView(
    setAppState: Callable[[Callable[[dict], dict]], None],
) -> None:
    """Exit teammate transcript view and return to leader's view.

    Mirrors exitTeammateView() from teammateViewHelpers.ts.
    """
    _log_event("tengu_transcript_view_exit", {})

    def updater(prev: dict) -> dict:
        id_ = prev.get("viewingAgentTaskId")
        cleared = {
            **prev,
            "viewingAgentTaskId": None,
            "viewSelectionMode": "none",
        }
        if id_ is None:
            return prev if prev.get("viewSelectionMode") == "none" else cleared
        task = prev.get("tasks", {}).get(id_)
        if not isLocalAgentTask(task) or not _task_get(task, "retain"):
            return cleared
        return {
            **cleared,
            "tasks": {**prev.get("tasks", {}), id_: _release(task)},
        }

    setAppState(updater)


def stopOrDismissAgent(
    taskId: str,
    setAppState: Callable[[Callable[[dict], dict]], None],
) -> None:
    """Context-sensitive x: running → abort, terminal → dismiss.

    Mirrors stopOrDismissAgent() from teammateViewHelpers.ts.
    """
    def updater(prev: dict) -> dict:
        task = prev.get("tasks", {}).get(taskId)
        if not isLocalAgentTask(task):
            return prev
        if _task_get(task, "status") == "running":
            abort = _task_get(task, "abortController", _task_get(task, "abort_controller"))
            if abort is not None:
                try:
                    abort.abort()
                except Exception:
                    pass
            return prev
        if _task_get(task, "evictAfter", _task_get(task, "evict_after")) == 0:
            return prev
        viewing_this = prev.get("viewingAgentTaskId") == taskId
        released = _task_replace(_release(task), evictAfter=0, evict_after=0)
        extra: dict = {}
        if viewing_this:
            extra = {"viewingAgentTaskId": None, "viewSelectionMode": "none"}
        return {
            **prev,
            "tasks": {**prev.get("tasks", {}), taskId: released},
            **extra,
        }

    setAppState(updater)
