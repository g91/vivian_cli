"""TaskCreateTool — mirrors src/tools/TaskCreateTool/TaskCreateTool.tsx"""
from __future__ import annotations
from typing import Any, Dict

from ...tasks.manager import TaskManager

TOOL_NAME = 'TaskCreate'

INPUT_SCHEMA = {
    "type": "object",
    "required": ['subject', 'description'],
    "properties": {
        'subject': {'type': 'string'},
        'description': {'type': 'string'},
        'activeForm': {'type': 'string'},
        'metadata': {'type': 'object'},
    },
}

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        'task': {
            'type': 'object',
            'properties': {
                'id': {'type': 'string'},
                'subject': {'type': 'string'},
            },
            'required': ['id', 'subject'],
        }
    },
}


async def description() -> str:
    return 'Create a new task.'


async def prompt() -> str:
    return 'Use this tool to create a new task for tracking work.'


async def call(input_data: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    subject = input_data.get('subject')
    description = input_data.get('description')
    if not subject or description is None:
        return {'error': 'subject and description are required'}

    task = TaskManager.get().create_todo(
        subject=str(subject),
        description=str(description),
        active_form=str(input_data.get('activeForm') or ''),
        metadata=dict(input_data.get('metadata') or {}),
    )
    return {
        'task': {
            'id': task.id,
            'subject': task.subject,
        }
    }
