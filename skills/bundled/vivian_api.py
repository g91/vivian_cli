"""vivianApi skill — mirrors src/skills/bundled/vivianApi.ts (feature-gated)."""
from __future__ import annotations

from typing import Any

from ..bundled_skills import BundledSkillDefinition, register_bundled_skill


def register_vivian_api_skill() -> None:
    register_bundled_skill(BundledSkillDefinition(
        name="vivianApi",
        description="Make direct Anthropic API calls with advanced options.",
        user_invocable=True,
        get_prompt_for_command=lambda args="", ctx=None: [
            {"type": "text", "text": (
                "# vivian API\n\n"
                "Help the user make direct calls to the Anthropic API.\n\n"
                f"Request: {args}"
            )}
        ],
    ))
