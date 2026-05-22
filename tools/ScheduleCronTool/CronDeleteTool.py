"""CronDeleteTool — mirrors src/tools/ScheduleCronTool/CronDeleteTool.ts"""
from __future__ import annotations
from typing import Any, Dict

from ...utils.cronTasks import listAllCronTasks, removeCronTasks

TOOL_NAME = "CronDelete"

INPUT_SCHEMA = {
    "type": "object",
    "required": ["id"],
    "properties": {
        "id": {
            "type": "string",
            "description": "The ID of the cron job to delete",
        },
    },
}

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "deleted": {"type": "boolean"},
    },
}

async def call(input_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """Delete a cron job by ID."""
    job_id = input_data.get("id", "")
    tasks = await listAllCronTasks(context.get("cwd") if isinstance(context, dict) else None)
    if not any(str(task.get("id")) == str(job_id) for task in tasks):
        return {"deleted": False, "error": f"No scheduled job with id '{job_id}'", "id": job_id}
    await removeCronTasks([job_id], context.get("cwd") if isinstance(context, dict) else None)
    return {
        "deleted": True,
        "id": job_id,
    }
