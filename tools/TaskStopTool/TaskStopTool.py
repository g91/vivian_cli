"""TaskStopTool — mirrors src/tools/TaskStopTool/TaskStopTool.tsx"""
from __future__ import annotations
from typing import Any, Dict

from ...tasks.stopTask import StopTaskError, stopTask

TOOL_NAME = 'TaskStop'

INPUT_SCHEMA = {
    "type": "object",
    "required": ['task_id'],
    "properties": {
        'task_id': {'type': 'string'},
        'shell_id': {'type': 'string'},
    },
}

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        'message': {'type': 'string'},
        'task_id': {'type': 'string'},
        'task_type': {'type': 'string'},
        'command': {'type': 'string'},
    },
}


async def description() -> str:
    return 'Stop a background task.'


async def prompt() -> str:
    return 'Use this tool to stop a running background task by ID.'


async def call(input_data: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    task_id = input_data.get('task_id') or input_data.get('shell_id')
    if not task_id:
        return {'error': 'Missing required parameter: task_id'}

    manager_context = context if isinstance(context, dict) else {}
    manager = manager_context.get('task_manager')
    if manager is None:
        from ...tasks.manager import TaskManager

        manager = TaskManager.get()

    def _get_app_state() -> dict[str, Any]:
        return {'tasks': getattr(manager, '_tasks', {})}

    def _set_app_state(updater):
        current = _get_app_state()
        updated = updater(current)
        if isinstance(updated, dict) and 'tasks' in updated:
            manager._tasks = updated['tasks']

    try:
        result = await stopTask(
            str(task_id),
            {
                'getAppState': _get_app_state,
                'setAppState': _set_app_state,
            },
        )
    except StopTaskError as error:
        return {'error': str(error)}

    return {
        'message': f"Successfully stopped task: {result['taskId']} ({result.get('command')})",
        'task_id': result['taskId'],
        'task_type': result['taskType'],
        'command': result.get('command') or '',
    }
