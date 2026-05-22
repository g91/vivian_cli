"""CronListTool — mirrors src/tools/ScheduleCronTool/CronListTool.ts"""
from __future__ import annotations
from typing import Any, Dict

from ...utils.cron import cronToHuman
from ...utils.cronTasks import listAllCronTasks

TOOL_NAME = "CronList"

INPUT_SCHEMA = {
    "type": "object",
    "properties": {},
}

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "jobs": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "schedule": {"type": "string"},
                    "command": {"type": "string"},
                    "name": {"type": "string"},
                },
            },
        },
    },
}

async def call(input_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """List all cron jobs."""
    del input_data
    tasks = await listAllCronTasks(context.get("cwd") if isinstance(context, dict) else None)
    return {
        "jobs": [
            {
                "id": task.get("id", ""),
                "schedule": task.get("cron", ""),
                "command": task.get("prompt", ""),
                "name": task.get("name", ""),
                "humanSchedule": cronToHuman(task.get("cron", "")),
            }
            for task in tasks
        ],
    }
