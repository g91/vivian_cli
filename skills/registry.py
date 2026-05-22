"""Skill registry — mirrors src/skills/."""

from __future__ import annotations

import logging
from typing import Any, Optional

from ..types import SkillDefinition

logger = logging.getLogger(__name__)


class SkillRegistry:
    """Central registry for all skills."""

    def __init__(self, skills: Optional[list[SkillDefinition]] = None):
        self._skills: dict[str, SkillDefinition] = {}
        if skills:
            for s in skills:
                self.register(s)

    def register(self, skill: SkillDefinition):
        self._skills[skill.name] = skill

    def get(self, name: str) -> Optional[SkillDefinition]:
        return self._skills.get(name)

    def get_enabled_skills(self) -> list[SkillDefinition]:
        return [s for s in self._skills.values() if s.is_enabled]

    def find_by_trigger(self, trigger: str) -> list[SkillDefinition]:
        return [
            s for s in self.get_enabled_skills()
            if trigger in s.triggers
        ]

    def __contains__(self, name: str) -> bool:
        return name in self._skills

    def __len__(self) -> int:
        return len(self._skills)


# ── Bundled Skills ─────────────────────────────────────────

BUNDLED_SKILLS: list[SkillDefinition] = [
    SkillDefinition(
        name="debug",
        description="Debug errors, stack traces, and test failures systematically",
        prompt="""You are a debugging expert. When debugging:
1. Read the error message carefully
2. Find the relevant source files
3. Identify the root cause
4. Apply a targeted fix
5. Verify the fix works""",
        source="bundled",
        triggers=["error", "debug", "traceback", "stack trace", "fix this"],
    ),
    SkillDefinition(
        name="batch",
        description="Process multiple files or items in batch",
        prompt="Process the requested items in batch. Handle errors gracefully and report results.",
        source="bundled",
        triggers=["batch", "all files", "every file"],
    ),
    SkillDefinition(
        name="simplify",
        description="Simplify complex code or explanations",
        prompt="Simplify the given code or concept. Make it more readable and maintainable.",
        source="bundled",
        triggers=["simplify", "refactor", "clean up"],
    ),
    SkillDefinition(
        name="verify",
        description="Verify that changes work correctly",
        prompt="Verify the changes by running tests, checking syntax, and reviewing logic.",
        source="bundled",
        triggers=["verify", "check", "test this", "validate"],
    ),
    SkillDefinition(
        name="remember",
        description="Store important information in memory",
        prompt="Extract key facts and store them in Vivian's memory for future reference.",
        source="bundled",
        triggers=["remember", "memorize", "store this", "save this"],
    ),
    SkillDefinition(
        name="loop",
        description="Handle iterative/looping tasks",
        prompt="Process the task iteratively, handling each item in sequence.",
        source="bundled",
        triggers=["loop", "for each", "iterate"],
    ),
    SkillDefinition(
        name="stuck",
        description="Help when you're stuck on a problem",
        prompt="Take a step back and approach the problem from different angles. Break it down into smaller pieces.",
        source="bundled",
        triggers=["stuck", "can't figure out", "not working"],
    ),
    SkillDefinition(
        name="updateConfig",
        description="Update Vivian's configuration",
        prompt="Update the specified configuration values safely.",
        source="bundled",
        triggers=["update config", "change setting"],
    ),
    SkillDefinition(
        name="skillify",
        description="Convert a workflow into a reusable skill",
        prompt="Analyze the workflow and create a reusable skill definition.",
        source="bundled",
        triggers=["create skill", "make this a skill"],
    ),
    SkillDefinition(
        name="scheduleRemoteAgents",
        description="Schedule agents to run remotely",
        prompt="Set up scheduled execution of agent tasks.",
        source="bundled",
        triggers=["schedule", "cron", "run daily"],
    ),
    SkillDefinition(
        name="keybindings",
        description="Help with keybinding configuration",
        prompt="Assist with viewing and customizing keyboard shortcuts.",
        source="bundled",
        triggers=["keybinding", "shortcut", "hotkey"],
    ),
    SkillDefinition(
        name="vivianApi",
        description="Work with the vivian/Anthropic API",
        prompt="Help with vivian API integration and usage.",
        source="bundled",
        triggers=["vivian api", "anthropic"],
    ),
    SkillDefinition(
        name="vivianInChrome",
        description="Use vivian in Chrome browser",
        prompt="Help with the vivian in Chrome extension.",
        source="bundled",
        triggers=["chrome", "browser extension"],
    ),
    SkillDefinition(
        name="loremIpsum",
        description="Generate placeholder text",
        prompt="Generate Lorem Ipsum placeholder text as requested.",
        source="bundled",
        triggers=["lorem", "placeholder", "dummy text"],
    ),
]


def register_all_skills(registry: SkillRegistry):
    """Register all bundled skills."""
    for skill in BUNDLED_SKILLS:
        registry.register(skill)
    return registry
