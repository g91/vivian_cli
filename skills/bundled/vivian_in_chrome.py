"""vivianInChrome skill — mirrors src/skills/bundled/vivianInChrome.ts."""
from __future__ import annotations

from typing import Any

from ..bundled_skills import BundledSkillDefinition, register_bundled_skill


def register_vivian_in_chrome_skill() -> None:
    register_bundled_skill(BundledSkillDefinition(
        name="vivianInChrome",
        description="Interact with the current Chrome browser tab via a browser extension.",
        user_invocable=True,
        get_prompt_for_command=lambda args="", ctx=None: [
            {"type": "text", "text": (
                "# vivian in Chrome\n\n"
                "Interact with the currently open Chrome tab using the browser extension.\n\n"
                f"Task: {args}"
            )}
        ],
    ))
