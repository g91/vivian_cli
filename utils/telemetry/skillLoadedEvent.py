"""Port of src/utils/telemetry/skillLoadedEvent.ts."""
from __future__ import annotations

import math
import os

from ...commands import getSkillToolCommands
from ...services.analytics.index import logEvent


SKILL_BUDGET_CONTEXT_PERCENT = 0.01
CHARS_PER_TOKEN = 4
DEFAULT_CHAR_BUDGET = 8_000


def _get_char_budget(contextWindowTokens=None) -> int:
    env_budget = os.environ.get("SLASH_COMMAND_TOOL_CHAR_BUDGET")
    if env_budget and env_budget.isdigit():
        return int(env_budget)
    if contextWindowTokens:
        return math.floor(contextWindowTokens * CHARS_PER_TOKEN * SKILL_BUDGET_CONTEXT_PERCENT)
    return DEFAULT_CHAR_BUDGET


async def logSkillsLoaded(cwd, contextWindowTokens):
    """Log a skill-loaded analytics event for each prompt skill available at startup."""
    skills = await getSkillToolCommands(cwd)
    skill_budget = _get_char_budget(contextWindowTokens)

    for skill in skills:
        skill_type = getattr(skill, "type", None) if not isinstance(skill, dict) else skill.get("type")
        if skill_type != "prompt":
            continue
        skill_name = getattr(skill, "name", None) if not isinstance(skill, dict) else skill.get("name")
        skill_source = getattr(skill, "source", None) if not isinstance(skill, dict) else skill.get("source")
        loaded_from = getattr(skill, "loaded_from", None) if not isinstance(skill, dict) else skill.get("loaded_from") or skill.get("loadedFrom")
        skill_kind = getattr(skill, "kind", None) if not isinstance(skill, dict) else skill.get("kind")
        logEvent(
            "tengu_skill_loaded",
            {
                "_PROTO_skill_name": skill_name,
                "skill_source": skill_source,
                "skill_loaded_from": loaded_from,
                "skill_budget": skill_budget,
                **({"skill_kind": skill_kind} if skill_kind else {}),
            },
        )


log_skills_loaded = logSkillsLoaded

