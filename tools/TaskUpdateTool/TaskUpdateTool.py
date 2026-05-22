"""TaskUpdateTool — mirrors src/tools/TaskUpdateTool/TaskUpdateTool.tsx"""
from __future__ import annotations
from typing import Any, Dict

from ...tasks.manager import TaskManager
from ...tasks.types import TodoTask

TOOL_NAME = 'TaskUpdate'

INPUT_SCHEMA = {
    "type": "object",
    "required": ['task_id'],
    "properties": {
        'task_id': {'type': 'string'},
        'taskId': {'type': 'string'},
        'subject': {'type': 'string'},
        'description': {'type': 'string'},
        'activeForm': {'type': 'string'},
        'status': {'type': 'string'},
        'owner': {'type': 'string'},
        'addBlocks': {'type': 'array', 'items': {'type': 'string'}},
        'addBlockedBy': {'type': 'array', 'items': {'type': 'string'}},
        'metadata': {'type': 'object'},
    },
}

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        'success': {'type': 'boolean'},
        'taskId': {'type': 'string'},
        'updatedFields': {'type': 'array', 'items': {'type': 'string'}},
        'error': {'type': 'string'},
        'statusChange': {
            'type': 'object',
            'properties': {
                'from': {'type': 'string'},
                'to': {'type': 'string'},
            },
        },
    },
}


async def description() -> str:
    return 'Update a task status or details.'


async def prompt() -> str:
    return 'Use this tool to update a task by ID.'


async def call(input_data: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    task_id = input_data.get('task_id') or input_data.get('taskId')
    if not task_id:
        return {'success': False, 'taskId': '', 'updatedFields': [], 'error': 'task_id is required'}

    manager = TaskManager.get()
    existing = manager.get_task(str(task_id))
    if existing is None or not isinstance(existing, TodoTask):
        return {'success': False, 'taskId': str(task_id), 'updatedFields': [], 'error': 'Task not found'}

    updated_fields: list[str] = []
    status_change = None
    status = input_data.get('status')

    if status == 'deleted':
        manager.update_todo(str(task_id), delete=True)
        return {
            'success': True,
            'taskId': str(task_id),
            'updatedFields': ['deleted'],
            'statusChange': {'from': existing.status, 'to': 'deleted'},
        }

    subject = input_data.get('subject')
    description = input_data.get('description')
    active_form = input_data.get('activeForm')
    owner = input_data.get('owner')
    add_blocks = list(input_data.get('addBlocks') or [])
    add_blocked_by = list(input_data.get('addBlockedBy') or [])
    metadata = input_data.get('metadata')

    if subject is not None and subject != existing.subject:
        updated_fields.append('subject')
    if description is not None and description != existing.description:
        updated_fields.append('description')
    if active_form is not None and active_form != existing.active_form:
        updated_fields.append('activeForm')
    if owner is not None and owner != existing.owner:
        updated_fields.append('owner')
    if add_blocks:
        updated_fields.append('addBlocks')
    if add_blocked_by:
        updated_fields.append('addBlockedBy')
    if metadata is not None:
        updated_fields.append('metadata')
    if status is not None and status != existing.status:
        updated_fields.append('status')
        status_change = {'from': existing.status, 'to': status}

    updated = manager.update_todo(
        str(task_id),
        subject=subject,
        description=description,
        active_form=active_form,
        status=status,
        owner=owner,
        add_blocks=add_blocks,
        add_blocked_by=add_blocked_by,
        metadata=metadata,
    )
    if updated is None:
        return {'success': False, 'taskId': str(task_id), 'updatedFields': [], 'error': 'Task not found'}

    result = {
        'success': True,
        'taskId': str(task_id),
        'updatedFields': updated_fields,
    }
    if status_change is not None:
        result['statusChange'] = status_change
    return result
