"""Dream task helpers mirroring src/tasks/DreamTask/DreamTask.ts."""

from __future__ import annotations

import time
from typing import Any, Callable, Optional

from ...Task import createTaskStateBase
from ...utils.abortController import create_abort_controller
from ...utils.task.framework import registerTask, updateTaskState
from ..types import DreamTaskState, DreamTurn


def isDreamTask(task: Any) -> bool:
    return (task.get("type") if isinstance(task, dict) else getattr(task, "type", None)) == "dream"


def registerDreamTask(taskId: str, setAppState: Callable[[Callable[[Any], Any]], None], opts: Optional[dict[str, Any]] = None) -> DreamTaskState:
    opts = opts or {}
    task = createTaskStateBase(
        taskId,
        "dream",
        opts.get("description", "Dream task"),
        cls=DreamTaskState,
        status="running",
        abort_controller=create_abort_controller(),
        prior_mtime=opts.get("prior_mtime", 0.0),
        sessions_reviewing=opts.get("sessions_reviewing", 0),
    )
    registerTask(task, setAppState)
    return task


def addDreamTurn(taskId: str, turn: DreamTurn, setAppState: Callable[[Callable[[Any], Any]], None]) -> None:
    updateTaskState(taskId, setAppState, lambda task: task if getattr(task, "status", None) != "running" else _update_turns(task, turn))


def _update_turns(task: Any, turn: DreamTurn) -> Any:
    task.turns = [*getattr(task, "turns", []), turn]
    task.phase = "updating"
    return task


def completeDreamTask(taskId: str, setAppState: Callable[[Callable[[Any], Any]], None]) -> None:
    updateTaskState(taskId, setAppState, lambda task: _finish(task, "completed", None))


def failDreamTask(taskId: str, error: str, setAppState: Callable[[Callable[[Any], Any]], None]) -> None:
    updateTaskState(taskId, setAppState, lambda task: _finish(task, "failed", error))


def _finish(task: Any, status: str, error: Optional[str]) -> Any:
    if getattr(task, "status", None) != "running":
        return task
    task.status = status
    task.end_time = time.time() * 1000
    if error is not None:
        task.error = error
    task.abort_controller = None
    return task


class _DreamTaskImpl:
    name = "DreamTask"
    type = "dream"

    async def kill(self, taskId: str, setAppState: Callable[[Callable[[Any], Any]], None]) -> None:
        def _kill(task: Any) -> Any:
            if getattr(task, "status", None) != "running":
                return task
            abort_controller = getattr(task, "abort_controller", None)
            if abort_controller is not None:
                abort_controller.abort()
            task.status = "killed"
            task.end_time = time.time() * 1000
            task.abort_controller = None
            return task

        updateTaskState(taskId, setAppState, _kill)


DreamTask = _DreamTaskImpl()