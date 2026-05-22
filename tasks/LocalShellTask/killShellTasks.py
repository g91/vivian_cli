"""Shell-task kill helpers mirroring src/tasks/LocalShellTask/killShellTasks.ts."""

from __future__ import annotations

from typing import Any, Callable

from .LocalShellTask import LocalShellTask
from .guards import isLocalShellTask


async def killTask(taskId: str, setAppState: Callable[[Callable[[Any], Any]], None]) -> None:
    await LocalShellTask.kill(taskId, setAppState)


async def killShellTasksForAgent(agentId: str, tasks: dict[str, Any], setAppState: Callable[[Callable[[Any], Any]], None]) -> None:
    for task_id, task in tasks.items():
        if isLocalShellTask(task) and getattr(task, "agent_id", None) == agentId:
            await LocalShellTask.kill(task_id, setAppState)