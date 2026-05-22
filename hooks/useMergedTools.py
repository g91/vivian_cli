"""Tool merging hook parity for src/hooks/useMergedTools.ts."""

from __future__ import annotations

from typing import Any

from ..tools import assembleToolPool
from ..utils.toolPool import mergeAndFilterTools


def useMergedTools(
    initialTools: list[Any],
    mcpTools: list[Any],
    toolPermissionContext: Any,
) -> list[Any]:
    assembled = assembleToolPool(toolPermissionContext, mcpTools)
    mode = getattr(toolPermissionContext, "mode", None)
    if isinstance(toolPermissionContext, dict):
        mode = toolPermissionContext.get("mode", mode)
    return mergeAndFilterTools(initialTools, assembled, mode)


use_merged_tools = useMergedTools
