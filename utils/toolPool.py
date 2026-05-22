"""Tool pool helpers mirroring src/utils/toolPool.ts."""

from __future__ import annotations

import os
from typing import Any

from ..constants import COORDINATOR_MODE_ALLOWED_TOOLS


PR_ACTIVITY_TOOL_SUFFIXES = [
    "subscribe_pr_activity",
    "unsubscribe_pr_activity",
]


def _tool_name(tool: Any) -> str:
    if isinstance(tool, dict):
        return str(tool.get("name", ""))
    return str(getattr(tool, "name", ""))


def _is_mcp_tool(tool: Any) -> bool:
    if isinstance(tool, dict):
        if tool.get("mcp_info") or tool.get("mcpInfo"):
            return True
    else:
        if getattr(tool, "mcp_info", None) or getattr(tool, "mcpInfo", None):
            return True
    return _tool_name(tool).startswith("mcp__")


def isPrActivitySubscriptionTool(name):
    return any(str(name).endswith(suffix) for suffix in PR_ACTIVITY_TOOL_SUFFIXES)


def applyCoordinatorToolFilter(tools):
    """Filters a tool array to the set allowed in coordinator mode."""
    allowed = {str(name).lower() for name in COORDINATOR_MODE_ALLOWED_TOOLS}
    return [
        tool
        for tool in (tools or [])
        if _tool_name(tool).lower() in allowed or isPrActivitySubscriptionTool(_tool_name(tool))
    ]


def mergeAndFilterTools(initialTools, assembled, mode):
    """Pure function that merges tool pools and applies coordinator mode filtering."""
    merged: dict[str, Any] = {}
    for tool in [*(initialTools or []), *(assembled or [])]:
        name = _tool_name(tool)
        if name and name not in merged:
            merged[name] = tool

    deduped = list(merged.values())
    built_in = sorted([tool for tool in deduped if not _is_mcp_tool(tool)], key=lambda tool: _tool_name(tool))
    mcp = sorted([tool for tool in deduped if _is_mcp_tool(tool)], key=lambda tool: _tool_name(tool))
    tools = [*built_in, *mcp]

    if str(mode) == "coordinator" or os.environ.get("COORDINATOR_MODE") in {"1", "true", "yes", "on"}:
        return applyCoordinatorToolFilter(tools)
    return tools


is_pr_activity_subscription_tool = isPrActivitySubscriptionTool
apply_coordinator_tool_filter = applyCoordinatorToolFilter
merge_and_filter_tools = mergeAndFilterTools

