"""ToolSearchTool — mirrors src/tools/ToolSearchTool/ToolSearchTool.tsx"""
from __future__ import annotations
import re
from typing import Any, Dict

from ...Tool import findToolByName
from ...types import ToolDefinition
from ...utils.debug_log import dlog as _dlog

TOOL_NAME = "ToolSearch"

INPUT_SCHEMA = {
    "type": "object",
    "required": ["query"],
    "properties": {
        "query": {
            "type": "string",
            "description": "Natural language description of the tool capability needed",
        },
        "max_results": {
            "type": "integer",
            "description": "Maximum number of results to return",
            "default": 5,
        },
    },
}

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "matches": {"type": "array", "items": {"type": "string"}},
        "query": {"type": "string"},
        "total_deferred_tools": {"type": "integer"},
    },
}


async def description() -> str:
    return "Search for available tools by natural language description."


async def prompt() -> str:
    return (
        "Use this tool to find available tools matching a natural language query. "
        "Returns tool names and descriptions for tools matching your query."
    )


def _get_tools(context: Any) -> list[ToolDefinition]:
    if isinstance(context, dict):
        registry = context.get("registry")
        if registry is not None and hasattr(registry, "get_enabled_tools"):
            return list(registry.get_enabled_tools())
        tools = context.get("tools")
        if isinstance(tools, list):
            return [tool for tool in tools if isinstance(tool, ToolDefinition)]
    return []


def _searchable_parts(tool: ToolDefinition) -> list[str]:
    parts = [tool.name, *(tool.aliases or []), tool.description]
    return [part.lower() for part in parts if isinstance(part, str) and part]


def _score_tool(tool: ToolDefinition, query: str) -> int:
    query_lower = query.lower().strip()
    if not query_lower:
        return 0

    searchable = _searchable_parts(tool)
    name = tool.name.lower()
    aliases = [alias.lower() for alias in tool.aliases or []]
    if name == query_lower or query_lower in aliases:
        return 100

    score = 0
    terms = [term for term in re.split(r"\s+", query_lower) if term]
    for term in terms:
        if name == term:
            score += 20
        if any(alias == term for alias in aliases):
            score += 18
        if term in name:
            score += 10
        if any(term in alias for alias in aliases):
            score += 8
        if any(term in part for part in searchable):
            score += 3
    return score


async def call(input_data: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    query = str(input_data.get("query") or "").strip()
    max_results = int(input_data.get("max_results") or 5)
    tools = _get_tools(context)

    if not query:
        return {"matches": [], "query": query, "total_deferred_tools": len(tools)}

    select_match = re.match(r"^select:(.+)$", query, flags=re.IGNORECASE)
    if select_match:
        requested = [item.strip() for item in select_match.group(1).split(",") if item.strip()]
        matches: list[str] = []
        for item in requested:
            tool = findToolByName(tools, item)
            if tool is not None and tool.name not in matches:
                matches.append(tool.name)
        _dlog("ToolSearchTool: select query=%r matches=%r", query, matches)
        return {
            "matches": matches,
            "query": query,
            "total_deferred_tools": len(tools),
        }

    exact = findToolByName(tools, query)
    if exact is not None:
        matches = [exact.name]
        _dlog("ToolSearchTool: exact query=%r match=%r", query, matches)
        return {
            "matches": matches,
            "query": query,
            "total_deferred_tools": len(tools),
        }

    scored = [
        (tool, _score_tool(tool, query))
        for tool in tools
    ]
    matches = [
        tool.name
        for tool, score in sorted(scored, key=lambda item: (-item[1], item[0].name.lower()))
        if score > 0
    ][:max_results]

    _dlog("ToolSearchTool: keyword query=%r matches=%r", query, matches)
    return {
        "matches": matches,
        "query": query,
        "total_deferred_tools": len(tools),
    }
