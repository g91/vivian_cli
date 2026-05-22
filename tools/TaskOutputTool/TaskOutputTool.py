"""TaskOutputTool — mirrors src/tools/TaskOutputTool/TaskOutputTool.tsx"""
from __future__ import annotations
from typing import Any, Dict

from ...tasks.manager import TaskManager

TOOL_NAME = 'TaskOutput'

INPUT_SCHEMA = {
    "type": "object",
    "required": ['task_id'],
    "properties": {
        'task_id': {'type': 'string'},
        'block': {'type': 'boolean', 'default': True},
        'timeout': {'type': 'number', 'default': 30000},
    },
}

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        'retrieval_status': {'type': 'string'},
        'task': {
            'anyOf': [
                {'type': 'null'},
                {'type': 'object'},
            ]
        },
    },
}


async def description() -> str:
    return 'Read the output stream of a background task.'


async def prompt() -> str:
    return 'Use this tool to read stdout/stderr from a background task.'


async def call(input_data: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    task_id = input_data.get('task_id')
    if not task_id:
        return {'error': 'Task ID is required'}

    block = bool(input_data.get('block', True))
    timeout_ms = float(input_data.get('timeout', 30000))
    timeout_s = max(timeout_ms, 0) / 1000.0

    manager = TaskManager.get()
    task = manager.get_task(str(task_id))
    if task is None:
        return {'error': f'No task found with ID: {task_id}'}

    result = await manager.get_task_output(str(task_id), block=block, timeout=timeout_s)
    retrieval_status = result.get('retrieval_status', 'not_ready')
    task_data = result.get('task')
    if isinstance(task_data, dict):
        task_data = {
            'task_id': task_data.get('id', str(task_id)),
            'task_type': task_data.get('type', ''),
            'status': task_data.get('status', ''),
            'description': task_data.get('description', ''),
            'output': task_data.get('output', '') or '',
            'exitCode': task_data.get('exit_code'),
            'error': result.get('error') or task_data.get('error'),
            **({'prompt': task_data.get('prompt')} if task_data.get('prompt') is not None else {}),
            **({'result': task_data.get('result')} if task_data.get('result') is not None else {}),
        }
    return {
        'retrieval_status': retrieval_status,
        'task': task_data,
    }
