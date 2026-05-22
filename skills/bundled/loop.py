"""Loop skill — mirrors src/skills/bundled/loop.ts (feature-gated)."""
from __future__ import annotations

from typing import Any

from ..bundled_skills import BundledSkillDefinition, register_bundled_skill


def register_loop_skill() -> None:
    register_bundled_skill(BundledSkillDefinition(
        name="loop",
        description="Continuously run a task on a schedule or trigger.",
        user_invocable=True,
        get_prompt_for_command=lambda args="", ctx=None: [
            {"type": "text", "text": (
                "# Loop: Continuous Task Execution\n\n"
                "Set up a continuous loop to execute a task on a schedule or trigger.\n\n"
                f"Task: {args}"
            )}
        ],
    ))
