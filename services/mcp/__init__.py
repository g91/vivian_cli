"""MCP package — mirrors src/services/mcp/."""
from __future__ import annotations

from .normalization import normalizeNameForMCP
from .envExpansion import expandEnvVarsInString
from .mcpStringUtils import (
    mcpInfoFromString,
    getMcpPrefix,
    buildMcpToolName,
    getToolNameForPermissionCheck,
    getMcpDisplayName,
    extractMcpToolDisplayName,
)

__all__ = [
    "normalizeNameForMCP",
    "expandEnvVarsInString",
    "mcpInfoFromString",
    "getMcpPrefix",
    "buildMcpToolName",
    "getToolNameForPermissionCheck",
    "getMcpDisplayName",
    "extractMcpToolDisplayName",
]
