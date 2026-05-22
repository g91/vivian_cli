"""Remote agent task helpers mirroring src/tasks/RemoteAgentTask/RemoteAgentTask.tsx."""

from __future__ import annotations

import json
import time
from typing import Any, Callable

from ...Task import createTaskStateBase
from ...utils.task.framework import registerTask, updateTaskState
from ..types import RemoteAgentTaskState


REMOTE_TASK_TYPES = ["remote-agent", "ultraplan", "ultrareview", "autofix-pr", "background-pr"]


def isRemoteAgentTask(task: Any) -> bool:
    return (task.get("type") if isinstance(task, dict) else getattr(task, "type", None)) == "remote_agent"


def extractReviewFromLog(log: list[dict[str, Any]]) -> str | None:
    for entry in reversed(log):
        review = entry.get("review")
        if isinstance(review, str) and review:
            return review
    return None


def extractReviewTagFromLog(log: list[dict[str, Any]]) -> str | None:
    for entry in reversed(log):
        tag = entry.get("reviewTag") or entry.get("review_tag")
        if isinstance(tag, str) and tag:
            return tag
    return None


def extractTodoListFromLog(log: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for entry in reversed(log):
        todo_list = entry.get("todoList") or entry.get("todo_list")
        if isinstance(todo_list, list):
            return todo_list
        line = entry.get("line")
        if isinstance(line, str):
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict) and isinstance(parsed.get("todoList"), list):
                return parsed["todoList"]
    return []


def registerRemoteAgentTask(taskId: str, sessionId: str, command: str, taskType: str, setAppState: Callable[[Callable[[Any], Any]], None]) -> RemoteAgentTaskState:
    task = createTaskStateBase(
        taskId,
        "remote_agent",
        command,
        cls=RemoteAgentTaskState,
        status="running",
        remote_task_type=taskType,
        session_id=sessionId,
        command=command,
        title=command,
        poll_started_at=time.time() * 1000,
        is_ultraplan=taskType == "ultraplan",
        is_remote_review=taskType == "ultrareview",
        is_long_running=taskType in {"autofix-pr", "background-pr"},
    )
    registerTask(task, setAppState)
    return task


class _RemoteAgentTaskImpl:
    name = "RemoteAgentTask"
    type = "remote_agent"

    async def kill(self, taskId: str, setAppState: Callable[[Callable[[Any], Any]], None]) -> None:
        def _kill(task: Any) -> Any:
            if getattr(task, "status", None) != "running":
                return task
            task.status = "killed"
            task.end_time = time.time() * 1000
            return task

        updateTaskState(taskId, setAppState, _kill)


RemoteAgentTask = _RemoteAgentTaskImpl()