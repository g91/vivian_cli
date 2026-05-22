"""ScheduleCronTool — mirrors src/tools/ScheduleCronTool/ScheduleCronTool.tsx"""
from __future__ import annotations
from typing import Any, Dict

from ...utils.cron import cronToHuman, parseCronExpression
from ...utils.cronTasks import addCronTask, listAllCronTasks, nextCronRunMs, removeCronTasks

TOOL_NAME = "ScheduleCron"

INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["create", "list", "delete"]},
        "schedule": {"type": "string", "description": "Cron expression (e.g. '0 * * * *')"},
        "command": {"type": "string", "description": "Command to run on schedule"},
        "description": {"type": "string"},
        "id": {"type": "string", "description": "Cron job id for delete"},
    },
}


async def description() -> str:
    return "Schedule a cron job."


async def prompt() -> str:
    return "Use this tool to schedule a cron job that runs a command on a schedule."


async def call(input_data: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    action = input_data.get("action") or ("delete" if input_data.get("id") else "create" if input_data.get("schedule") and input_data.get("command") else "list")
    cwd = context.get("cwd") if isinstance(context, dict) and context.get("cwd") else None

    if action == "list":
        tasks = await listAllCronTasks(cwd)
        jobs = [
            {
                "id": task.get("id", ""),
                "schedule": task.get("cron", ""),
                "command": task.get("prompt", ""),
                "name": task.get("name", ""),
                "humanSchedule": cronToHuman(task.get("cron", "")),
            }
            for task in tasks
        ]
        return {"jobs": jobs}

    if action == "delete":
        job_id = input_data.get("id")
        if not job_id:
            return {"success": False, "message": "id is required for delete"}
        await removeCronTasks([job_id], cwd)
        return {"deleted": True, "id": job_id}

    schedule = input_data.get("schedule")
    command = input_data.get("command")
    if not schedule or not command:
        return {"success": False, "message": "schedule and command are required for create"}
    if parseCronExpression(str(schedule)) is None:
        return {"success": False, "message": f"Invalid cron expression '{schedule}'"}
    if nextCronRunMs(str(schedule), __import__('time').time() * 1000) is None:
        return {"success": False, "message": f"Cron expression '{schedule}' does not match any upcoming time"}
    task_id = await addCronTask(str(schedule), str(command), True, True, dir=cwd)
    return {
        "id": task_id,
        "schedule": str(schedule),
        "command": str(command),
        "description": input_data.get("description", ""),
        "humanSchedule": cronToHuman(str(schedule)),
    }
