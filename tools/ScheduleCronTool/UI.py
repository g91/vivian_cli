"""ScheduleCronTool UI — mirrors src/tools/ScheduleCronTool/UI.tsx"""
from typing import Any, Dict, Optional

def renderToolUseMessage(inputData: Dict[str, Any]) -> str:
    """Render the tool use message for ScheduleCronTool."""
    action = inputData.get("action", "list")
    if action == "create":
        schedule = str(inputData.get("schedule") or "")
        command = str(inputData.get("command") or "")
        if command:
            command = command[:60] + ("..." if len(command) > 60 else "")
            return f"{schedule}: {command}"
        return schedule
    if action == "delete":
        return str(inputData.get("id") or "")
    return ""

def renderToolResultMessage(output: Dict[str, Any]) -> Optional[str]:
    """Render the tool result message for ScheduleCronTool."""
    if output.get("success") is False:
        return str(output.get("message") or "Cron error")

    if "jobs" in output:
        jobs = output["jobs"]
        if not jobs:
            return "No scheduled jobs"
        lines = []
        for job in jobs:
            lines.append(f"{job.get('id', '')} {job.get('humanSchedule', '')}".rstrip())
        return "\n".join(lines)

    if "deleted" in output:
        return f"Cancelled {output.get('id', '')}"

    if "id" in output:
        human_schedule = output.get("humanSchedule")
        if human_schedule:
            return f"Scheduled {output['id']} ({human_schedule})"
        return f"Scheduled {output['id']}"

    return None

def renderToolUseErrorMessage(errorMessage: str) -> str:
    """Render an error message for ScheduleCronTool."""
    return f"Cron error: {errorMessage}"
