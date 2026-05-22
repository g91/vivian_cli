"""Check if a tool can be used — mirrors src/hooks/useCanUseTool.ts."""
from __future__ import annotations
from typing import Any

def useCanUseTool(toolName: str, permissionContext: Any = None) -> bool:
    """Check if a tool is permitted to run."""
    try:
        if permissionContext is None:
            return True
        if hasattr(permissionContext, 'can_use_tool'):
            return permissionContext.can_use_tool(toolName)
        if isinstance(permissionContext, dict):
            denied = permissionContext.get('deniedTools', [])
            return toolName not in denied
        return True
    except Exception:
        return True

use_can_use_tool = useCanUseTool
