"""
Port of src/utils/plugins/loadPluginCommands.ts

Loads plugin commands and skills from plugin directories.
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Any, Dict, List, Optional, Set

from ..debug import logForDebugging
from ..frontmatterParser import parseFrontmatter
from ..fsOperations import getFsImplementation, isDuplicatePath
from ..markdownConfigLoader import extractDescriptionFromMarkdown, parseSlashCommandToolsFromFrontmatter
from .pluginLoader import loadAllPluginsCacheOnly
from .pluginOptionsStorage import substitutePluginVariables
from .walkPluginMarkdown import walkPluginMarkdown


async def _load_commands_from_directory(
    commands_path: str,
    plugin_name: str,
    source_name: str,
    plugin_path: str,
    plugin_manifest: Dict[str, Any],
    loaded_paths: Set[str],
    is_skill_mode: bool = False,
) -> List[Dict[str, Any]]:
    commands: List[Dict[str, Any]] = []

    async def _on_file(full_path: str, namespace: List[str]) -> None:
        fs = getFsImplementation()
        if isDuplicatePath(fs, full_path, loaded_paths):
            return
        try:
            content = await fs.readFile(full_path, encoding="utf-8")
            frontmatter, markdown_content = parseFrontmatter(content, full_path)

            is_skill = os.path.basename(full_path).lower() == "skill.md"
            base_name = os.path.basename(full_path).replace(".md", "")
            if is_skill:
                base_name = os.path.basename(os.path.dirname(full_path))

            name_parts = [plugin_name, *namespace, base_name]
            command_name = ":".join(name_parts)

            description = frontmatter.get("description") or extractDescriptionFromMarkdown(
                markdown_content, "Plugin skill" if is_skill else "Plugin command"
            )

            allowed_tools = parseSlashCommandToolsFromFrontmatter(frontmatter.get("allowed-tools"))
            argument_hint = frontmatter.get("argument-hint")

            commands.append({
                "type": "prompt",
                "name": command_name,
                "description": str(description),
                "allowedTools": allowed_tools,
                "argumentHint": argument_hint,
                "source": "plugin",
                "pluginInfo": {"pluginManifest": plugin_manifest, "repository": source_name},
                "isHidden": False,
                "progressMessage": "loading" if is_skill else "running",
            })
        except Exception as e:
            logForDebugging(f"Failed to load command from {full_path}: {e}", level="error")

    await walkPluginMarkdown(commands_path, _on_file, stop_at_skill_dir=True, log_label="commands")
    return commands


@lru_cache(maxsize=1)
def _get_plugin_commands_cached() -> List[Dict[str, Any]]:
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_load_plugin_commands())
    finally:
        loop.close()


async def _load_plugin_commands() -> List[Dict[str, Any]]:
    result = await loadAllPluginsCacheOnly()
    enabled = result.get("enabled", [])
    all_commands: List[Dict[str, Any]] = []

    for plugin in enabled:
        loaded_paths: Set[str] = set()
        if getattr(plugin, "commandsPath", None):
            cmds = await _load_commands_from_directory(
                plugin.commandsPath, plugin.name, plugin.source,
                plugin.path, plugin.manifest, loaded_paths,
            )
            all_commands.extend(cmds)

    return all_commands


async def getPluginCommands() -> List[Dict[str, Any]]:
    return _get_plugin_commands_cached()


async def getPluginSkills() -> List[Dict[str, Any]]:
    result = await loadAllPluginsCacheOnly()
    enabled = result.get("enabled", [])
    all_skills: List[Dict[str, Any]] = []

    for plugin in enabled:
        loaded_paths: Set[str] = set()
        if getattr(plugin, "skillsPath", None):
            skills = await _load_commands_from_directory(
                plugin.skillsPath, plugin.name, plugin.source,
                plugin.path, plugin.manifest, loaded_paths, is_skill_mode=True,
            )
            all_skills.extend(skills)

    return all_skills


def clearPluginCommandCache() -> None:
    _get_plugin_commands_cached.cache_clear()


def clearPluginSkillsCache() -> None:
    _get_plugin_commands_cached.cache_clear()

