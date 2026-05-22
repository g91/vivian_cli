"""Tools module — mirrors src/tools.ts."""

from __future__ import annotations

from typing import Any, Optional

from ..Tool import findToolByName, getEmptyToolPermissionContext, toolMatchesName
from ..constants import ALL_BASE_TOOLS
from .all_tools import register_all_tools
from .registry import ToolRegistry
from .utils import (
    tagMessagesWithToolUseID,
    getToolUseIDFromParentMessage,
    # legacy snake_case
    tag_messages_with_tool_use_id,
    get_tool_use_id_from_parent_message,
)


_registry_cache: Optional[ToolRegistry] = None


def _get_registry() -> ToolRegistry:
    global _registry_cache
    if _registry_cache is None:
        registry = ToolRegistry()
        register_all_tools(registry)
        _registry_cache = registry
    return _registry_cache


def getAllBaseTools() -> list[Any]:
    registry = _get_registry()
    return [tool for tool in registry.get_enabled_tools() if tool.name.lower() in set(ALL_BASE_TOOLS)]


def filterToolsByDenyRules(tools: list[Any], permissionContext: dict[str, Any]) -> list[Any]:
    deny_rules = (permissionContext or {}).get("alwaysDenyRules", {}) or {}
    filtered: list[Any] = []
    for tool in tools:
        name = getattr(tool, "name", None)
        if name is None and isinstance(tool, dict):
            name = tool.get("name")
        if not name:
            filtered.append(tool)
            continue
        rule = deny_rules.get(name)
        if isinstance(rule, dict) and rule.get("ruleContent"):
            filtered.append(tool)
            continue
        if rule is None:
            filtered.append(tool)
    return filtered


def getTools(permissionContext: dict[str, Any]) -> list[Any]:
    registry = _get_registry()
    tools = registry.get_enabled_tools()
    return filterToolsByDenyRules(tools, permissionContext)


def assembleToolPool(permissionContext: dict[str, Any], mcpTools: list[Any]) -> list[Any]:
    built_in_tools = getTools(permissionContext)
    filtered_mcp_tools = filterToolsByDenyRules(mcpTools, permissionContext)
    by_name: dict[str, Any] = {}
    for tool in [*built_in_tools, *filtered_mcp_tools]:
        name = getattr(tool, "name", None)
        if name is None and isinstance(tool, dict):
            name = tool.get("name")
        if isinstance(name, str) and name not in by_name:
            by_name[name] = tool
    return list(by_name.values())


def getMergedTools(permissionContext: dict[str, Any], mcpTools: list[Any]) -> list[Any]:
    return assembleToolPool(permissionContext, mcpTools)


def clearToolsCache() -> None:
    global _registry_cache
    _registry_cache = None


get_all_base_tools = getAllBaseTools
filter_tools_by_deny_rules = filterToolsByDenyRules
get_tools = getTools
assemble_tool_pool = assembleToolPool
get_merged_tools = getMergedTools
clear_tools_cache = clearToolsCache

__all__ = [
    "ToolRegistry",
    "register_all_tools",
    "assembleToolPool",
    "assemble_tool_pool",
    "clearToolsCache",
    "clear_tools_cache",
    "filterToolsByDenyRules",
    "filter_tools_by_deny_rules",
    "findToolByName",
    "getAllBaseTools",
    "getEmptyToolPermissionContext",
    "getMergedTools",
    "getTools",
    "get_all_base_tools",
    "get_merged_tools",
    "get_tools",
    # camelCase (primary)
    "tagMessagesWithToolUseID",
    "getToolUseIDFromParentMessage",
    "toolMatchesName",
    # snake_case aliases
    "findToolByName",
    "tag_messages_with_tool_use_id",
    "get_tool_use_id_from_parent_message",
    "toolMatchesName",
]
