"""Top-level tool helpers mirroring src/Tool.ts."""

from __future__ import annotations

from typing import Any, Optional

from .types import ToolDefinition


def getEmptyToolPermissionContext() -> dict[str, Any]:
    return {
        "mode": "default",
        "additionalWorkingDirectories": {},
        "alwaysAllowRules": {},
        "alwaysDenyRules": {},
        "alwaysAskRules": {},
        "isBypassPermissionsModeAvailable": False,
    }


def toolMatchesName(
    tool: dict[str, Any] | ToolDefinition | Any,
    name: str,
) -> bool:
    target = name.lower()
    tool_name = getattr(tool, "name", None)
    if tool_name is None and isinstance(tool, dict):
        tool_name = tool.get("name")
    if isinstance(tool_name, str) and tool_name.lower() == target:
        return True

    aliases = getattr(tool, "aliases", None)
    if aliases is None and isinstance(tool, dict):
        aliases = tool.get("aliases", [])
    return any(isinstance(alias, str) and alias.lower() == target for alias in (aliases or []))


def findToolByName(
    tools: list[dict[str, Any]] | list[ToolDefinition] | list[Any],
    name: str,
) -> Optional[Any]:
    for tool in tools:
        if toolMatchesName(tool, name):
            return tool
    return None


get_empty_tool_permission_context = getEmptyToolPermissionContext
tool_matches_name = toolMatchesName
find_tool_by_name = findToolByName


__all__ = [
    "findToolByName",
    "find_tool_by_name",
    "getEmptyToolPermissionContext",
    "get_empty_tool_permission_context",
    "toolMatchesName",
    "tool_matches_name",
]