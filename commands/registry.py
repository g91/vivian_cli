"""Command registry — mirrors src/commands.ts and src/commands/*."""

from __future__ import annotations

import logging
from typing import Any, Optional, Callable

from ..types import CommandDefinition, CommandType

logger = logging.getLogger(__name__)


class CommandRegistry:
    """Central registry for all commands."""

    def __init__(self, commands: Optional[list[CommandDefinition]] = None):
        self._commands: dict[str, CommandDefinition] = {}
        self._handlers: dict[str, Callable] = {}
        if commands:
            for c in commands:
                self.register(c)

    def register(self, command: CommandDefinition, handler: Optional[Callable] = None):
        self._commands[command.name] = command
        for alias in command.aliases:
            self._commands[alias] = command
        if handler:
            self._handlers[command.name] = handler

    def register_handler(self, name: str, loader: Callable):
        """Register a lazy-loading handler for a command."""
        self._handlers[name] = loader

    def get_handler(self, name: str) -> Optional[Callable]:
        """Get a command handler, resolving lazy loaders."""
        h = self._handlers.get(name)
        if h is None:
            return None
        if hasattr(h, '__call__') and not hasattr(h, '__code__'):
            # It's a loader function — call it to get the real handler
            try:
                real = h()
                self._handlers[name] = real
                return real
            except Exception as e:
                logger.warning("Failed to load handler for %s: %s", name, e)
                return None
        return h

    def get(self, name: str) -> Optional[CommandDefinition]:
        return self._commands.get(name)

    def get_enabled_commands(self) -> list[CommandDefinition]:
        seen = set()
        result = []
        for c in self._commands.values():
            if c.name not in seen and c.is_enabled:
                seen.add(c.name)
                result.append(c)
        return result

    def get_skills(self) -> list[CommandDefinition]:
        """Get commands that are skills (model-invocable)."""
        return [
            c for c in self.get_enabled_commands()
            if c.type == CommandType.PROMPT and not c.disable_model_invocation
        ]

    def get_slash_commands(self) -> list[CommandDefinition]:
        """Get commands that are user-facing slash commands."""
        return [
            c for c in self.get_enabled_commands()
            if c.type in (CommandType.LOCAL, CommandType.LOCAL_JSX)
        ]

    def filter_remote_safe(self) -> list[CommandDefinition]:
        """Get commands safe for remote mode."""
        from ..constants import REMOTE_SAFE_COMMANDS
        return [
            c for c in self.get_enabled_commands()
            if c.name in REMOTE_SAFE_COMMANDS
        ]

    def filter_bridge_safe(self) -> list[CommandDefinition]:
        """Get commands safe for bridge mode."""
        from ..constants import BRIDGE_SAFE_COMMANDS
        return [
            c for c in self.get_enabled_commands()
            if c.name in BRIDGE_SAFE_COMMANDS
        ]

    def find(self, name: str) -> Optional[CommandDefinition]:
        return self._commands.get(name)

    def has(self, name: str) -> bool:
        return name in self._commands

    async def execute(self, name: str, args: Optional[dict] = None) -> Any:
        handler = self._handlers.get(name)
        if handler:
            if asyncio.iscoroutinefunction(handler):
                return await handler(args or {})
            return handler(args or {})
        return None

    def __contains__(self, name: str) -> bool:
        return name in self._commands

    def __len__(self) -> int:
        return len(set(c.name for c in self._commands.values()))


import asyncio
