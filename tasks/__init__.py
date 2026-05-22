"""Vivian task system — background shell tasks, agent tasks, and exact task modules."""

from __future__ import annotations

import os
import time
from typing import Any, Callable

from .types import (
    AgentProgress,
    AgentTask,
    BackgroundTaskState,
    DreamTaskState,
    DreamTurn,
    InProcessTeammateTaskState,
    LocalAgentTaskState,
    LocalShellTaskState,
    RemoteAgentTaskState,
    ShellTask,
    TaskBase,
    TaskState,
    TaskStatus,
    TaskType,
    TodoTask,
    is_background_task,
)
from .manager import TaskManager
from .pillLabel import getPillLabel, pillNeedsCta
from .pill_label import format_task_summary, get_pill_label
from .LocalShellTask.LocalShellTask import LocalShellTask, looksLikePrompt
from .LocalShellTask.guards import isLocalShellTask
from .LocalAgentTask.LocalAgentTask import LocalAgentTask, isLocalAgentTask
from .InProcessTeammateTask.InProcessTeammateTask import InProcessTeammateTask
from .DreamTask.DreamTask import DreamTask, isDreamTask, registerDreamTask
from .RemoteAgentTask.RemoteAgentTask import REMOTE_TASK_TYPES, RemoteAgentTask, isRemoteAgentTask, registerRemoteAgentTask
from .stopTask import StopTaskError, stopTask
from .stop_task import stop_task


class _TodoTaskImpl:
    name = "TodoTask"
    type = "todo"

    async def kill(self, taskId: str, setAppState: Callable[[Callable[[Any], Any]], None]) -> None:
        def _kill(prev: Any) -> Any:
            prev_tasks = prev.get("tasks", {}) if isinstance(prev, dict) else getattr(prev, "tasks", {})
            task = prev_tasks.get(taskId)
            if task is None:
                return prev
            status = task.get("status") if isinstance(task, dict) else getattr(task, "status", None)
            if status != "running":
                return prev

            if isinstance(task, dict):
                updated_task = dict(task)
                updated_task["status"] = "stopped"
                updated_task["end_time"] = time.time() * 1000
                updated_tasks = dict(prev_tasks)
                updated_tasks[taskId] = updated_task
                if isinstance(prev, dict):
                    next_state = dict(prev)
                    next_state["tasks"] = updated_tasks
                    return next_state
                setattr(prev, "tasks", updated_tasks)
                return prev

            task.status = "stopped"
            task.end_time = time.time() * 1000
            return prev

        setAppState(_kill)


TodoTaskImpl = _TodoTaskImpl()


def _feature(name: str) -> bool:
    value = os.environ.get(name)
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


LocalWorkflowTask = None
MonitorMcpTask = None

if _feature("WORKFLOW_SCRIPTS"):
    try:
        from .LocalWorkflowTask.LocalWorkflowTask import LocalWorkflowTask as _LocalWorkflowTask

        LocalWorkflowTask = _LocalWorkflowTask
    except Exception:
        LocalWorkflowTask = None

if _feature("MONITOR_TOOL"):
    try:
        from .MonitorMcpTask.MonitorMcpTask import MonitorMcpTask as _MonitorMcpTask

        MonitorMcpTask = _MonitorMcpTask
    except Exception:
        MonitorMcpTask = None


TASKS_BY_TYPE = {
    "local_bash": LocalShellTask,
    "local_agent": LocalAgentTask,
    "remote_agent": RemoteAgentTask,
    "in_process_teammate": InProcessTeammateTask,
    "dream": DreamTask,
    "todo": TodoTaskImpl,
}

if LocalWorkflowTask is not None:
    TASKS_BY_TYPE["local_workflow"] = LocalWorkflowTask

if MonitorMcpTask is not None:
    TASKS_BY_TYPE["monitor_mcp"] = MonitorMcpTask


def getAllTasks():
    tasks = [
        LocalShellTask,
        LocalAgentTask,
        RemoteAgentTask,
        DreamTask,
    ]
    if LocalWorkflowTask is not None:
        tasks.append(LocalWorkflowTask)
    if MonitorMcpTask is not None:
        tasks.append(MonitorMcpTask)
    return tasks


def getTaskByType(task_type: str):
    return TASKS_BY_TYPE.get(task_type)


def get_all_tasks():
    return getAllTasks()


def get_task_by_type(task_type: str):
    return getTaskByType(task_type)


def is_local_shell_task(obj: object) -> bool:
    return isLocalShellTask(obj)


def looks_like_prompt(tail: str) -> bool:
    return looksLikePrompt(tail)


def is_local_agent_task(obj: object) -> bool:
    return isLocalAgentTask(obj)


def is_dream_task(obj: object) -> bool:
    return isDreamTask(obj)


def register_dream_task(*args, **kwargs):
    return registerDreamTask(*args, **kwargs)


def is_remote_agent_task(obj: object) -> bool:
    return isRemoteAgentTask(obj)


def register_remote_agent_task(*args, **kwargs):
    return registerRemoteAgentTask(*args, **kwargs)


__all__ = [
    "AgentProgress",
    "AgentTask",
    "BackgroundTaskState",
    "DreamTask",
    "DreamTaskState",
    "DreamTurn",
    "InProcessTeammateTask",
    "InProcessTeammateTaskState",
    "LocalAgentTask",
    "LocalAgentTaskState",
    "LocalShellTask",
    "LocalShellTaskState",
    "REMOTE_TASK_TYPES",
    "RemoteAgentTask",
    "RemoteAgentTaskState",
    "ShellTask",
    "StopTaskError",
    "TaskBase",
    "TaskManager",
    "TaskState",
    "TaskStatus",
    "TaskType",
    "TodoTask",
    "format_task_summary",
    "getPillLabel",
    "getAllTasks",
    "getTaskByType",
    "get_all_tasks",
    "get_pill_label",
    "get_task_by_type",
    "isDreamTask",
    "isLocalAgentTask",
    "isLocalShellTask",
    "isRemoteAgentTask",
    "is_background_task",
    "is_dream_task",
    "is_local_agent_task",
    "is_local_shell_task",
    "is_remote_agent_task",
    "looksLikePrompt",
    "looks_like_prompt",
    "pillNeedsCta",
    "registerDreamTask",
    "registerRemoteAgentTask",
    "register_dream_task",
    "register_remote_agent_task",
    "stopTask",
    "stop_task",
]
