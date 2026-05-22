"""ScheduleRemoteAgents skill — mirrors src/skills/bundled/scheduleRemoteAgents.ts."""
from __future__ import annotations

from typing import Any

from ..bundled_skills import BundledSkillDefinition, register_bundled_skill


def register_schedule_remote_agents_skill() -> None:
    register_bundled_skill(BundledSkillDefinition(
        name="scheduleRemoteAgents",
        description="Schedule tasks for remote agents to run asynchronously.",
        user_invocable=True,
        get_prompt_for_command=lambda args="", ctx=None: [
            {"type": "text", "text": (
                "# Schedule Remote Agents\n\n"
                "Schedule tasks for remote agents to execute asynchronously.\n\n"
                f"Instruction: {args}"
            )}
        ],
    ))
