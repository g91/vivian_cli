"""Tool registry — manages all tools, mirrors src/tools.ts and src/Tool.ts."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Optional, Callable

from ..types import ToolDefinition, ToolSource, Message
from ..constants import (
    ALL_BASE_TOOLS,
    ALL_AGENT_DISALLOWED_TOOLS,
    COORDINATOR_MODE_ALLOWED_TOOLS,
)
from ..utils.debug_log import dlog as _dlog

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Central registry for all tools."""

    def __init__(self, tools: Optional[list[ToolDefinition]] = None):
        self._tools: dict[str, ToolDefinition] = {}
        self._handlers: dict[str, Callable] = {}
        if tools:
            for t in tools:
                self.register(t)

    def register(self, tool: ToolDefinition, handler: Optional[Callable] = None):
        """Register a tool definition and optional handler."""
        self._tools[tool.name] = tool
        for alias in tool.aliases:
            self._tools[alias] = tool
        if handler:
            self._handlers[tool.name] = handler

    def unregister(self, name: str):
        tool = self._tools.pop(name, None)
        if tool:
            for alias in tool.aliases:
                self._tools.pop(alias, None)
            self._handlers.pop(name, None)

    def get(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def get_handler(self, name: str) -> Optional[Callable]:
        # First try the raw name, then resolve through the canonical tool name
        # so that aliases registered on ToolDefinition always find their handler.
        handler = self._handlers.get(name)
        if handler is not None:
            return handler
        tool = self._tools.get(name)
        if tool is not None:
            return self._handlers.get(tool.name)
        return None

    def get_enabled_tools(self) -> list[ToolDefinition]:
        seen = set()
        result = []
        for t in self._tools.values():
            if t.name not in seen and t.is_enabled:
                seen.add(t.name)
                result.append(t)
        return result

    def get_tools_for_agent(self) -> list[ToolDefinition]:
        """Get tools allowed for sub-agents."""
        return [
            t for t in self.get_enabled_tools()
            if t.name not in ALL_AGENT_DISALLOWED_TOOLS
        ]

    def get_tools_for_coordinator(self) -> list[ToolDefinition]:
        """Get tools allowed in coordinator mode."""
        return [
            t for t in self.get_enabled_tools()
            if t.name in COORDINATOR_MODE_ALLOWED_TOOLS
        ]

    def filter_by_deny_rules(
        self, deny_rules: dict[str, Any]
    ) -> list[ToolDefinition]:
        """Filter tools by deny rules from permission context."""
        result = []
        for t in self.get_enabled_tools():
            if t.name not in deny_rules:
                result.append(t)
        return result

    async def execute_tool(
        self, name: str, args: dict[str, Any], context: Optional[dict] = None
    ) -> Any:
        """Execute a tool by name with arguments."""
        tool = self.get(name)
        if not tool:
            logger.warning("[tool] NOT FOUND: %s", name)
            _dlog("registry: NOT FOUND %r — registered tools: %s", name, sorted(self._tools.keys()))
            return {"error": f"Tool not found: {name}"}

        handler = self.get_handler(name)
        if not handler:
            logger.warning("[tool] NO HANDLER: %s", name)
            _dlog("registry: NO HANDLER for %r", name)
            return {"error": f"No handler for tool: {name}"}

        # Build a compact arg summary for the log line
        try:
            _arg_summary = json.dumps(args, default=str, ensure_ascii=False)
            if len(_arg_summary) > 120:
                _arg_summary = _arg_summary[:117] + "..."
        except Exception:
            _arg_summary = repr(args)[:120]

        canonical = tool.name  # may differ from the alias used
        logger.info("[tool] ▶  %s  %s", canonical, _arg_summary)
        _dlog("registry: ▶ execute %r  args=%s", canonical, _arg_summary)
        _start = time.monotonic()

        try:
            if asyncio.iscoroutinefunction(handler):
                result = await handler(args, context)
            else:
                result = handler(args, context)

            elapsed_ms = (time.monotonic() - _start) * 1000
            # Summarise the result for the log
            try:
                _res_summary = json.dumps(result, default=str, ensure_ascii=False)
                if len(_res_summary) > 120:
                    _res_summary = _res_summary[:117] + "..."
            except Exception:
                _res_summary = repr(result)[:120]

            if isinstance(result, dict) and "error" in result:
                logger.warning("[tool] ✗  %s  (%.0f ms)  %s", canonical, elapsed_ms, _res_summary)
                _dlog("registry: ✗ %r  (%.0f ms)  %s", canonical, elapsed_ms, _res_summary)
            else:
                logger.info("[tool] ✔  %s  (%.0f ms)  %s", canonical, elapsed_ms, _res_summary)
                _dlog("registry: ✔ %r  (%.0f ms)  %s", canonical, elapsed_ms, _res_summary)

            return result

        except Exception as e:
            elapsed_ms = (time.monotonic() - _start) * 1000
            logger.error("[tool] ✗  %s  (%.0f ms)  %s: %s",
                         canonical, elapsed_ms, type(e).__name__, e)
            _dlog("registry: EXCEPTION %r  (%.0f ms)  %s: %s", canonical, elapsed_ms, type(e).__name__, e)
            return {"error": str(e)}

    def to_openai_schemas(self) -> list[dict[str, Any]]:
        """Convert all enabled tools to OpenAI function schemas."""
        return [t.to_openai_schema() for t in self.get_enabled_tools()]

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def __len__(self) -> int:
        return len(set(t.name for t in self._tools.values()))


# Extend ToolDefinition with schema generation
def _tool_to_openai_schema(self: ToolDefinition) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": self.name,
            "description": self.description,
            "parameters": self.input_schema or {
                "type": "object",
                "properties": {},
            },
        },
    }


ToolDefinition.to_openai_schema = _tool_to_openai_schema

import asyncio
