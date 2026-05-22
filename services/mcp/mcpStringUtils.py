"""MCP string utilities — mirrors src/services/mcp/mcpStringUtils.ts."""
from __future__ import annotations

from typing import Optional

from .normalization import normalizeNameForMCP


def mcpInfoFromString(tool_string: str) -> Optional[dict]:
    """Extract MCP server information from a tool name string.

    Expected format: "mcp__serverName__toolName"
    Mirrors mcpInfoFromString() from mcpStringUtils.ts.
    """
    parts = tool_string.split("__")
    if len(parts) < 2 or parts[0] != "mcp":
        return None
    server_name = parts[1]
    if not server_name:
        return None
    tool_name = "__".join(parts[2:]) if len(parts) > 2 else None
    return {"serverName": server_name, "toolName": tool_name}


def getMcpPrefix(server_name: str) -> str:
    """Generate the MCP tool/command name prefix for a given server.

    Mirrors getMcpPrefix() from mcpStringUtils.ts.
    """
    return f"mcp__{normalizeNameForMCP(server_name)}__"


def buildMcpToolName(server_name: str, tool_name: str) -> str:
    """Build a fully qualified MCP tool name.

    Mirrors buildMcpToolName() from mcpStringUtils.ts.
    """
    return f"{getMcpPrefix(server_name)}{normalizeNameForMCP(tool_name)}"


def getToolNameForPermissionCheck(tool: dict) -> str:
    """Get the name to use for permission rule matching.

    Mirrors getToolNameForPermissionCheck() from mcpStringUtils.ts.
    """
    mcp_info = tool.get("mcpInfo")
    if mcp_info:
        return buildMcpToolName(mcp_info["serverName"], mcp_info["toolName"])
    return tool.get("name", "")


def getMcpDisplayName(full_name: str, server_name: str) -> str:
    """Extract the display name from an MCP tool/command name.

    Mirrors getMcpDisplayName() from mcpStringUtils.ts.
    """
    prefix = f"mcp__{normalizeNameForMCP(server_name)}__"
    return full_name.replace(prefix, "", 1)


def extractMcpToolDisplayName(user_facing_name: str) -> str:
    """Extract just the tool display name from a user-facing name.

    Mirrors extractMcpToolDisplayName() from mcpStringUtils.ts.
    """
    without_suffix = user_facing_name.rstrip().removesuffix("(MCP)").strip()
    dash_index = without_suffix.find(" - ")
    if dash_index != -1:
        return without_suffix[dash_index + 3:].strip()
    return without_suffix


mcp_info_from_string = mcpInfoFromString
get_mcp_prefix = getMcpPrefix
build_mcp_tool_name = buildMcpToolName
get_tool_name_for_permission_check = getToolNameForPermissionCheck
get_mcp_display_name = getMcpDisplayName
extract_mcp_tool_display_name = extractMcpToolDisplayName
