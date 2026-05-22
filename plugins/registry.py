"""Plugin system — mirrors src/plugins/."""

from __future__ import annotations

import logging
from typing import Any, Optional

from ..types import PluginDefinition, ToolDefinition, CommandDefinition, SkillDefinition

logger = logging.getLogger(__name__)


class PluginRegistry:
    """Manages installed plugins."""

    def __init__(self):
        self._plugins: dict[str, PluginDefinition] = {}

    def register(self, plugin: PluginDefinition):
        self._plugins[plugin.name] = plugin
        logger.info(f"Registered plugin: {plugin.name} v{plugin.version}")

    def unregister(self, name: str):
        self._plugins.pop(name, None)

    def get(self, name: str) -> Optional[PluginDefinition]:
        return self._plugins.get(name)

    def get_all(self) -> list[PluginDefinition]:
        return list(self._plugins.values())

    def get_all_tools(self) -> list[ToolDefinition]:
        tools = []
        for p in self._plugins.values():
            tools.extend(p.tools)
        return tools

    def get_all_commands(self) -> list[CommandDefinition]:
        commands = []
        for p in self._plugins.values():
            commands.extend(p.commands)
        return commands

    def get_all_skills(self) -> list[SkillDefinition]:
        skills = []
        for p in self._plugins.values():
            skills.extend(p.skills)
        return skills

    def get_all_hooks(self) -> dict[str, Any]:
        hooks = {}
        for p in self._plugins.values():
            hooks.update(p.hooks)
        return hooks

    def clear(self):
        self._plugins.clear()

    def __contains__(self, name: str) -> bool:
        return name in self._plugins

    def __len__(self) -> int:
        return len(self._plugins)
