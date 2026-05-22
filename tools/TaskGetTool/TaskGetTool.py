"""TaskGetTool — mirrors src/tools/TaskGetTool/TaskGetTool.tsx"""
from __future__ import annotations
from typing import Any, Dict

from ...tasks.manager import TaskManager
from ...tasks.types import TodoTask

TOOL_NAME = 'TaskGet'

INPUT_SCHEMA = {
    "type": "object",
    "required": ['task_id'],
    "properties": {
        'task_id': {'type': 'string'},
        'taskId': {'type': 'string'},
    },
}

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "task": {
            "anyOf": [
                {"type": "null"},
                {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "subject": {"type": "string"},
                        "description": {"type": "string"},
                        "status": {"type": "string"},
                        "blocks": {"type": "array", "items": {"type": "string"}},
                        "blockedBy": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["id", "subject", "description", "status", "blocks", "blockedBy"],
                },
            ],
        },
    },
}


async def description() -> str:
    return 'Get the status and output of a background task.'


async def prompt() -> str:
    return 'Use this tool to get detailed information about a specific task by ID.'


async def call(input_data: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    task_id = input_data.get('task_id') or input_data.get('taskId')
    if not task_id:
        return {'error': 'task_id is required'}

    task = TaskManager.get().get_task(str(task_id))
    if task is None or not isinstance(task, TodoTask):
        return {'task': None}

    return {
        'task': {
            'id': task.id,
            'subject': task.subject,
            'description': task.description,
            'status': task.status,
            'blocks': list(task.blocks),
            'blockedBy': list(task.blocked_by),
        }
    }
