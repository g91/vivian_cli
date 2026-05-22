"""SkillTool — mirrors src/tools/SkillTool/SkillTool.tsx"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

from ...skills.bundled import init_bundled_skills
from ...skills.bundled_skills import get_bundled_skills
from ...skills.load_skills_dir import load_skills_dir

TOOL_NAME = "Skill"

INPUT_SCHEMA = {
    "type": "object",
    "required": ["skill_name"],
    "properties": {
        "skill_name": {"type": "string", "description": "Name of the skill to execute"},
        "arguments": {"type": "object", "description": "Arguments for the skill"},
    },
}


async def description() -> str:
    return "Execute a named skill or instruction set."


async def prompt() -> str:
    return "Use this tool to execute a named skill defined in the workspace or user config."


_BUNDLED_SKILLS_READY = False


def _ensure_bundled_skills() -> None:
    global _BUNDLED_SKILLS_READY
    if _BUNDLED_SKILLS_READY:
        return
    init_bundled_skills()
    _BUNDLED_SKILLS_READY = True


def _stringify_arguments(arguments: Any) -> str:
    if arguments is None:
        return ""
    if isinstance(arguments, str):
        return arguments
    if isinstance(arguments, (int, float, bool)):
        return str(arguments)
    try:
        return json.dumps(arguments, ensure_ascii=True, sort_keys=True)
    except TypeError:
        return str(arguments)


def _flatten_prompt_blocks(blocks: Any) -> str:
    if isinstance(blocks, str):
        return blocks
    if isinstance(blocks, dict):
        if blocks.get("type") == "text":
            return str(blocks.get("text", ""))
        return json.dumps(blocks, ensure_ascii=True, sort_keys=True)
    if isinstance(blocks, list):
        parts: list[str] = []
        for block in blocks:
            text = _flatten_prompt_blocks(block)
            if text:
                parts.append(text)
        return "\n\n".join(parts)
    return str(blocks)


def _skill_dirs(context: Any) -> list[Path]:
    cwd: str
    if isinstance(context, dict) and context.get("cwd"):
        cwd = str(context["cwd"])
    else:
        cwd = os.getcwd()
    return [
        Path.home() / ".vivian" / "skills",
        Path(cwd) / ".vivian" / "skills",
    ]


def _custom_skill_commands(context: Any) -> list[dict[str, Any]]:
    commands: list[dict[str, Any]] = []
    for directory in _skill_dirs(context):
        for skill in load_skills_dir(directory):
            commands.append(
                {
                    "type": "prompt",
                    "name": skill.name,
                    "description": skill.description,
                    "aliases": skill.aliases or [],
                    "allowed_tools": skill.allowed_tools or [],
                    "argument_hint": skill.argument_hint,
                    "when_to_use": skill.when_to_use,
                    "model": skill.model,
                    "source": "custom",
                    "loaded_from": str(directory),
                    "get_prompt_for_command": skill.get_prompt_for_command,
                }
            )
    return commands


def _all_skill_commands(context: Any) -> list[dict[str, Any]]:
    _ensure_bundled_skills()
    return [*get_bundled_skills(), *_custom_skill_commands(context)]


def _find_skill_command(skill_name: str, context: Any) -> dict[str, Any] | None:
    lowered = skill_name.lower()
    for command in _all_skill_commands(context):
        name = str(command.get("name", ""))
        if name.lower() == lowered:
            return command
        aliases = command.get("aliases") or []
        if any(str(alias).lower() == lowered for alias in aliases):
            return command
    return None


def _invoke_prompt_factory(prompt_factory: Any, args: str, context: Any) -> Any:
    if not callable(prompt_factory):
        return ""
    try:
        return prompt_factory(args, context)
    except TypeError:
        try:
            return prompt_factory(args)
        except TypeError:
            return prompt_factory()


async def call(input_data: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    skill_name = str(input_data.get("skill_name") or input_data.get("skill") or "").strip()
    if not skill_name:
        return {"result": None, "error": "Missing skill_name"}

    command = _find_skill_command(skill_name, context)
    if command is None:
        available = sorted(str(item.get("name", "")) for item in _all_skill_commands(context) if item.get("name"))
        return {
            "result": None,
            "error": f'Skill "{skill_name}" not found. Available skills: {", ".join(available)}',
        }

    args = _stringify_arguments(input_data.get("arguments"))
    prompt_factory = command.get("get_prompt_for_command")
    if callable(prompt_factory):
        prompt_value = _invoke_prompt_factory(prompt_factory, args, context)
    else:
        prompt_value = command.get("prompt") or ""

    result_text = _flatten_prompt_blocks(prompt_value)
    return {
        "result": result_text,
        "skill_name": command.get("name", skill_name),
        "source": command.get("source", "bundled"),
        "loaded_from": command.get("loaded_from"),
        "allowed_tools": command.get("allowed_tools") or [],
        "model": command.get("model"),
    }
