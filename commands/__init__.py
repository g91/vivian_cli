"""Commands module mirroring the top-level helpers from src/commands.ts."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..constants import BRIDGE_SAFE_COMMANDS, REMOTE_SAFE_COMMANDS
from ..types import CommandDefinition, getCommandName, isCommandEnabled
from ..skills.bundled import init_bundled_skills
from ..skills.bundled_skills import get_bundled_skills
from ..skills.load_skills_dir import load_skills_dir
from .all_commands import COMMANDS, register_all_commands
from .registry import CommandRegistry


_registry_cache: Optional[CommandRegistry] = None
_built_in_command_names_cache: Optional[set[str]] = None
_bundled_skills_ready = False


def _get_registry() -> CommandRegistry:
	global _registry_cache
	if _registry_cache is None:
		registry = CommandRegistry()
		register_all_commands(registry)
		_registry_cache = registry
	return _registry_cache


def builtInCommandNames() -> set[str]:
	global _built_in_command_names_cache
	if _built_in_command_names_cache is None:
		names: set[str] = set()
		for command in COMMANDS:
			names.add(command.name)
			names.update(command.aliases or [])
		_built_in_command_names_cache = names
	return set(_built_in_command_names_cache)


def meetsAvailabilityRequirement(cmd: CommandDefinition) -> bool:
	return bool(getattr(cmd, "is_enabled", True))


async def getCommands(cwd: str) -> list[CommandDefinition]:
	del cwd
	registry = _get_registry()
	return [command for command in registry.get_enabled_commands() if meetsAvailabilityRequirement(command)]


def clearCommandMemoizationCaches() -> None:
	global _built_in_command_names_cache
	_built_in_command_names_cache = None


def clearCommandsCache() -> None:
	global _registry_cache
	_registry_cache = None
	clearCommandMemoizationCaches()


def getMcpSkillCommands(mcpCommands: list[CommandDefinition]) -> list[CommandDefinition]:
	return [command for command in mcpCommands if getattr(command, "type", None) == getattr(command, "type", None)]


def _ensure_bundled_skills() -> None:
	global _bundled_skills_ready
	if _bundled_skills_ready:
		return
	init_bundled_skills()
	_bundled_skills_ready = True


def _skill_command_definition(raw: dict, default_source: str) -> CommandDefinition:
	return CommandDefinition(
		name=str(raw.get("name", "")),
		description=str(raw.get("description", "")),
		type="prompt",
		source=str(raw.get("source", default_source)),
		aliases=list(raw.get("aliases") or []),
		content_length=int(raw.get("content_length") or 0),
		progress_message=str(raw.get("progress_message") or "running"),
		is_enabled=True,
		loaded_from=raw.get("loaded_from"),
		disable_model_invocation=bool(raw.get("disable_model_invocation", False)),
	)


def _iter_custom_skill_commands(cwd: str) -> list[dict]:
	commands: list[dict] = []
	for directory in (Path.home() / ".vivian" / "skills", Path(cwd) / ".vivian" / "skills"):
		for skill in load_skills_dir(directory):
			commands.append(
				{
					"name": skill.name,
					"description": skill.description,
					"type": "prompt",
					"source": "custom",
					"aliases": skill.aliases or [],
					"loaded_from": str(directory),
					"disable_model_invocation": skill.disable_model_invocation,
				}
			)
	return commands


async def getSkillToolCommands(cwd: str) -> list[CommandDefinition]:
	_ensure_bundled_skills()
	commands: list[CommandDefinition] = []
	seen: set[str] = set()
	for raw in [*get_bundled_skills(), *_iter_custom_skill_commands(cwd)]:
		name = str(raw.get("name", ""))
		if not name or name in seen:
			continue
		if raw.get("is_hidden"):
			continue
		commands.append(_skill_command_definition(raw, "bundled"))
		seen.add(name)
	return commands


async def getSlashCommandToolSkills(cwd: str) -> list[CommandDefinition]:
	return await getSkillToolCommands(cwd)


def isBridgeSafeCommand(cmd: CommandDefinition) -> bool:
	return cmd.name in BRIDGE_SAFE_COMMANDS


def filterCommandsForRemoteMode(commands: list[CommandDefinition]) -> list[CommandDefinition]:
	return [command for command in commands if command.name in REMOTE_SAFE_COMMANDS]


def findCommand(commandName: str, commands: list[CommandDefinition]):
	lowered = commandName.lower()
	for command in commands:
		aliases = getattr(command, "aliases", []) or []
		if command.name.lower() == lowered or any(alias.lower() == lowered for alias in aliases):
			return command
	return None


def hasCommand(commandName: str, commands: list[CommandDefinition]) -> bool:
	return findCommand(commandName, commands) is not None


def getCommand(commandName: str, commands: list[CommandDefinition]) -> CommandDefinition:
	command = findCommand(commandName, commands)
	if command is None:
		raise KeyError(f"Unknown command: {commandName}")
	return command


def formatDescriptionWithSource(cmd: CommandDefinition) -> str:
	description = cmd.description
	source = getattr(cmd, "source", "builtin")
	loaded_from = getattr(cmd, "loaded_from", None)
	if source == "builtin":
		return description
	if loaded_from:
		return f"{description} ({source}: {loaded_from})"
	return f"{description} ({source})"


built_in_command_names = builtInCommandNames
meets_availability_requirement = meetsAvailabilityRequirement
get_commands = getCommands
clear_command_memoization_caches = clearCommandMemoizationCaches
clear_commands_cache = clearCommandsCache
get_mcp_skill_commands = getMcpSkillCommands
get_skill_tool_commands = getSkillToolCommands
get_slash_command_tool_skills = getSlashCommandToolSkills
is_bridge_safe_command = isBridgeSafeCommand
filter_commands_for_remote_mode = filterCommandsForRemoteMode
find_command = findCommand
has_command = hasCommand
get_command = getCommand
format_description_with_source = formatDescriptionWithSource


__all__ = [
	"BRIDGE_SAFE_COMMANDS",
	"COMMANDS",
	"CommandRegistry",
	"REMOTE_SAFE_COMMANDS",
	"builtInCommandNames",
	"built_in_command_names",
	"clearCommandMemoizationCaches",
	"clearCommandsCache",
	"clear_command_memoization_caches",
	"clear_commands_cache",
	"filterCommandsForRemoteMode",
	"filter_commands_for_remote_mode",
	"findCommand",
	"find_command",
	"formatDescriptionWithSource",
	"format_description_with_source",
	"getCommand",
	"getCommands",
	"getMcpSkillCommands",
	"getSkillToolCommands",
	"getSlashCommandToolSkills",
	"get_command",
	"get_commands",
	"get_mcp_skill_commands",
	"get_skill_tool_commands",
	"get_slash_command_tool_skills",
	"hasCommand",
	"has_command",
	"isBridgeSafeCommand",
	"is_bridge_safe_command",
	"meetsAvailabilityRequirement",
	"meets_availability_requirement",
	"register_all_commands",
	"getCommandName",
	"isCommandEnabled",
]
