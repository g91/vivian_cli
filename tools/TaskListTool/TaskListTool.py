"""TaskListTool — mirrors src/tools/TaskListTool/TaskListTool.tsx"""
from __future__ import annotations
from typing import Any, Dict

from ...tasks.manager import TaskManager
from ...tasks.types import TodoTask

TOOL_NAME = 'TaskList'

INPUT_SCHEMA = {
    "type": "object",
    "required": [],
    "properties": {},
}

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "tasks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "subject": {"type": "string"},
                    "status": {"type": "string"},
                    "owner": {"type": "string"},
                    "blockedBy": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["id", "subject", "status", "blockedBy"],
            },
        },
    },
}


async def description() -> str:
    return 'List all background tasks.'


async def prompt() -> str:
    return 'Use this tool to list structured tasks in the current task list.'


async def call(input_data: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    manager = TaskManager.get()
    todo_tasks = [task for task in manager.list_tasks() if isinstance(task, TodoTask)]

    visible_tasks = [
        task for task in todo_tasks
        if not getattr(task, 'metadata', {}).get('_internal')
    ]
    resolved_ids = {
        task.id for task in visible_tasks if getattr(task, 'status', None) == 'completed'
    }

    tasks = []
    for task in visible_tasks:
        tasks.append(
            {
                'id': task.id,
                'subject': task.subject,
                'status': task.status,
                'owner': task.owner,
                'blockedBy': [blocked for blocked in task.blocked_by if blocked not in resolved_ids],
            }
        )

    return {'tasks': tasks}
