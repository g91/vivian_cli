"""Main-session task helpers mirroring src/tasks/LocalMainSessionTask.ts."""

from __future__ import annotations

import time
from typing import Any, Callable

from ..Task import createTaskStateBase, generateTaskId
from ..utils.task.framework import registerTask, updateTaskState
from .types import LocalAgentTaskState


def isMainSessionTask(task: Any) -> bool:
    task_type = task.get("type") if isinstance(task, dict) else getattr(task, "type", None)
    agent_type = task.get("agent_type") if isinstance(task, dict) else getattr(task, "agent_type", None)
    return task_type == "local_agent" and agent_type == "main-session"


def registerMainSessionTask(description: str, prompt: str, setAppState: Callable[[Callable[[Any], Any]], None], toolUseId: str | None = None) -> LocalAgentTaskState:
    task_id = generateTaskId("local_agent")
    task = createTaskStateBase(
        task_id,
        "local_agent",
        description,
        toolUseId,
        cls=LocalAgentTaskState,
        status="running",
        agent_id=task_id,
        prompt=prompt,
        agent_type="main-session",
        is_backgrounded=True,
        pending_messages=[],
        retain=True,
        disk_loaded=False,
    )
    registerTask(task, setAppState)
    return task


def completeMainSessionTask(taskId: str, setAppState: Callable[[Callable[[Any], Any]], None]) -> None:
    updateTaskState(taskId, setAppState, lambda task: _finish_main_task(task, "completed"))


def foregroundMainSessionTask(taskId: str, setAppState: Callable[[Callable[[Any], Any]], None]) -> None:
    updateTaskState(taskId, setAppState, lambda task: _foreground(task))


def enqueueMainSessionNotification(*_: Any, **__: Any) -> None:
    return None


def startBackgroundSession(description: str, prompt: str, setAppState: Callable[[Callable[[Any], Any]], None], toolUseId: str | None = None) -> LocalAgentTaskState:
    return registerMainSessionTask(description, prompt, setAppState, toolUseId)


def _finish_main_task(task: Any, status: str) -> Any:
    if getattr(task, "status", None) != "running":
        return task
    task.status = status
    task.end_time = time.time() * 1000
    return task


def _foreground(task: Any) -> Any:
    task.is_backgrounded = False
    return task