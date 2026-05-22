"""Hooks system — mirrors src/hooks/ and src/schemas/hooks.ts."""

from __future__ import annotations

import logging
from typing import Any, Optional, Callable

from ..types import HookDefinition

logger = logging.getLogger(__name__)


class HookRegistry:
    """Manages lifecycle hooks for the application."""

    def __init__(self):
        self._hooks: dict[str, list[HookDefinition]] = {
            "pre_tool_use": [],
            "post_tool_use": [],
            "session_start": [],
            "session_end": [],
            "pre_compact": [],
            "post_compact": [],
            "notification": [],
            "stop": [],
            "subagent_start": [],
            "subagent_stop": [],
            "pre_message": [],
            "post_message": [],
        }
        self._handlers: dict[str, Callable] = {}

    def register(self, hook: HookDefinition, handler: Optional[Callable] = None):
        if hook.event in self._hooks:
            self._hooks[hook.event].append(hook)
        if handler:
            self._handlers[hook.name] = handler

    def get_hooks(self, event: str) -> list[HookDefinition]:
        return self._hooks.get(event, [])

    async def run_hooks(self, event: str, context: Optional[dict] = None) -> list[Any]:
        """Run all hooks for an event. Returns list of results."""
        results = []
        for hook in self.get_hooks(event):
            if not hook.is_enabled:
                continue
            handler = self._handlers.get(hook.name)
            if handler:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        result = await handler(context or {})
                    else:
                        result = handler(context or {})
                    results.append(result)
                except Exception as e:
                    logger.error(f"Hook {hook.name} error: {e}")
        return results

    def clear(self):
        for event in self._hooks:
            self._hooks[event].clear()
        self._handlers.clear()


import asyncio
