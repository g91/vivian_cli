"""In-process teammate task helpers mirroring src/tasks/InProcessTeammateTask/InProcessTeammateTask.tsx."""

from __future__ import annotations

import time
from typing import Any, Callable

from ...Task import isTerminalTaskStatus
from ...utils.task.framework import updateTaskState
from .types import appendCappedMessage, isInProcessTeammateTask


class _InProcessTeammateTaskImpl:
    name = "InProcessTeammateTask"
    type = "in_process_teammate"

    async def kill(self, taskId: str, setAppState: Callable[[Callable[[Any], Any]], None]) -> None:
        def _kill(task: Any) -> Any:
            if getattr(task, "status", None) != "running":
                return task
            abort_controller = getattr(task, "abort_controller", None)
            if abort_controller is not None:
                abort_controller.abort()
            current_abort = getattr(task, "current_work_abort_controller", None)
            if current_abort is not None:
                current_abort.abort()
            cleanup = getattr(task, "unregister_cleanup", None)
            if callable(cleanup):
                cleanup()
            task.status = "killed"
            task.end_time = time.time() * 1000
            task.unregister_cleanup = None
            return task

        updateTaskState(taskId, setAppState, _kill)


InProcessTeammateTask = _InProcessTeammateTaskImpl()


def requestTeammateShutdown(taskId: str, setAppState: Callable[[Callable[[Any], Any]], None]) -> None:
    updateTaskState(taskId, setAppState, lambda task: task if getattr(task, "status", None) != "running" or getattr(task, "shutdown_requested", False) else _request_shutdown(task))


def _request_shutdown(task: Any) -> Any:
    task.shutdown_requested = True
    return task


def appendTeammateMessage(taskId: str, message: Any, setAppState: Callable[[Callable[[Any], Any]], None]) -> None:
    def _append(task: Any) -> Any:
        if getattr(task, "status", None) != "running":
            return task
        task.messages = appendCappedMessage(getattr(task, "messages", None), message)
        return task

    updateTaskState(taskId, setAppState, _append)


def injectUserMessageToTeammate(taskId: str, message: str, setAppState: Callable[[Callable[[Any], Any]], None]) -> None:
    def _inject(task: Any) -> Any:
        if isTerminalTaskStatus(getattr(task, "status", "pending")):
            return task
        task.pending_user_messages = [*getattr(task, "pending_user_messages", []), message]
        task.messages = appendCappedMessage(getattr(task, "messages", None), {"role": "user", "content": message})
        return task

    updateTaskState(taskId, setAppState, _inject)


def findTeammateTaskByAgentId(agentId: str, tasks: dict[str, Any]) -> Any | None:
    fallback = None
    for task in tasks.values():
        identity = getattr(task, "identity", None)
        candidate_agent_id = getattr(identity, "agent_id", None) if identity is not None else None
        if isInProcessTeammateTask(task) and candidate_agent_id == agentId:
            if getattr(task, "status", None) == "running":
                return task
            if fallback is None:
                fallback = task
    return fallback


def getAllInProcessTeammateTasks(tasks: dict[str, Any]) -> list[Any]:
    return [task for task in tasks.values() if isInProcessTeammateTask(task)]


def getRunningTeammatesSorted(tasks: dict[str, Any]) -> list[Any]:
    teammates = [task for task in getAllInProcessTeammateTasks(tasks) if getattr(task, "status", None) == "running"]
    return sorted(teammates, key=lambda task: getattr(getattr(task, "identity", None), "agent_name", ""))