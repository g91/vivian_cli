"""skills command — mirrors src/commands/skills/skills.tsx.

Lists all available skills (prompt commands) that the AI can invoke.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


def formatSkills(skills: list) -> str:
    if not skills:
        return "No skills available."
    lines = ["Available Skills:", ""]
    for s in skills:
        if isinstance(s, str):
            name = s
            desc = ""
        elif isinstance(s, dict):
            name = s.get("name", "")
            desc = s.get("description", "")
        else:
            name = getattr(s, "name", "")
            desc = getattr(s, "description", "")
        lines.append(f"  • {name}: {desc}")
    return "\n".join(lines)


def _extend_unique(items: list, seen: set[str], values) -> None:
    for value in values or []:
        if isinstance(value, dict):
            name = str(value.get("name", "") or "")
        else:
            name = str(getattr(value, "name", "") or value or "")
        if not name or name in seen:
            continue
        seen.add(name)
        items.append(value)


async def call(args: str, context: CommandContext) -> TextResult:
    from ...types.command import TextResult

    skills = []
    seen: set[str] = set()
    try:
        skill_registry = getattr(context, "skill_registry", None)
        command_registry = getattr(context, "command_registry", None)
        registry = getattr(context, "registry", None)
        qe = getattr(context, "query_engine", None)

        if skill_registry is None and qe is not None:
            skill_registry = getattr(qe, "skill_registry", None)
        if command_registry is None and qe is not None:
            command_registry = getattr(qe, "command_registry", None)

        if skill_registry and hasattr(skill_registry, "get_enabled_skills"):
            _extend_unique(skills, seen, skill_registry.get_enabled_skills())
        if command_registry and hasattr(command_registry, "get_skills"):
            _extend_unique(skills, seen, command_registry.get_skills())
        if registry and hasattr(registry, "get_skills"):
            _extend_unique(skills, seen, registry.get_skills())
    except Exception:
        skills = []

    if skills:
        return TextResult(formatSkills(skills))
    return TextResult("No skills registry available.")


format_skills = formatSkills
