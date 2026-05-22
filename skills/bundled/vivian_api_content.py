"""vivianApiContent skill — mirrors src/skills/bundled/vivianApiContent.ts."""
from __future__ import annotations

from typing import Any

from ..bundled_skills import BundledSkillDefinition, register_bundled_skill


def register_vivian_api_content_skill() -> None:
    register_bundled_skill(BundledSkillDefinition(
        name="vivianApiContent",
        description="Generate structured content using the vivian API format.",
        user_invocable=False,
        get_prompt_for_command=lambda args="", ctx=None: [
            {"type": "text", "text": (
                "Generate structured content using the vivian API message format.\n\n"
                f"Args: {args}"
            )}
        ],
    ))
