"""CronCreateTool — mirrors src/tools/ScheduleCronTool/CronCreateTool.ts"""
from __future__ import annotations
from typing import Any, Dict

from ...utils.cron import cronToHuman, parseCronExpression
from ...utils.cronTasks import addCronTask, listAllCronTasks, nextCronRunMs

TOOL_NAME = "CronCreate"

INPUT_SCHEMA = {
    "type": "object",
    "required": ["cron", "prompt"],
    "properties": {
        "cron": {
            "type": "string",
            "description": "Cron expression (e.g., '0 9 * * *' for daily at 9am)",
        },
        "prompt": {
            "type": "string",
            "description": "The prompt to execute on schedule",
        },
        "recurring": {"type": "boolean"},
        "durable": {"type": "boolean"},
    },
}

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "schedule": {"type": "string"},
        "command": {"type": "string"},
    },
}

async def call(input_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new cron job."""
    cron = str(input_data.get("cron", ""))
    prompt = str(input_data.get("prompt", ""))
    recurring = bool(input_data.get("recurring", True))
    durable = bool(input_data.get("durable", False))

    if parseCronExpression(cron) is None:
        return {"error": f"Invalid cron expression '{cron}'"}
    if nextCronRunMs(cron, __import__('time').time() * 1000) is None:
        return {"error": f"Cron expression '{cron}' does not match any upcoming time"}
    tasks = await listAllCronTasks(context.get("cwd") if isinstance(context, dict) else None)
    if len(tasks) >= 50:
        return {"error": "Too many scheduled jobs (max 50)."}
    job_id = await addCronTask(
        cron,
        prompt,
        recurring,
        durable,
        dir=context.get("cwd") if isinstance(context, dict) else None,
    )
    return {
        "id": job_id,
        "humanSchedule": cronToHuman(cron),
        "recurring": recurring,
        "durable": durable,
    }
