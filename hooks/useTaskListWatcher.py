"""Task list watcher hook — mirrors src/hooks/useTaskListWatcher.ts."""
from __future__ import annotations
from typing import Any, Callable

def useTaskListWatcher(
    onChange: Callable[[list[Any]], None] | None = None,
) -> dict[str, Any]:
    """Watch and manage task list changes."""
    tasks = []
    
    def updateTasks(newTasks: list[Any]) -> None:
        nonlocal tasks
        tasks = list(newTasks)
        if onChange:
            onChange(tasks)
    
    return {
        'tasks': tasks,
        'updateTasks': updateTasks,
        'loading': False,
    }

use_task_list_watcher = useTaskListWatcher
