"""Background task navigation — mirrors src/hooks/useBackgroundTaskNavigation.ts."""
from __future__ import annotations
from typing import Any

def useBackgroundTaskNavigation() -> dict[str, Any]:
    """Navigate and manage background tasks."""
    tasks = []
    
    def addTask(task: dict) -> None:
        tasks.append(task)
    
    def removeTask(taskId: str) -> None:
        tasks[:] = [t for t in tasks if t.get('id') != taskId]
    
    def getTasks() -> list[dict]:
        return list(tasks)
    
    return {
        "tasks": tasks,
        "addTask": addTask,
        "removeTask": removeTask,
        "getTasks": getTasks,
    }

use_background_task_navigation = useBackgroundTaskNavigation
