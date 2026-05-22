"""ListMcpResourcesTool UI — mirrors src/tools/ListMcpResourcesTool/UI.tsx."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional


def renderToolUseMessage(inputData: Optional[Dict[str, Any]] = None) -> str:
    """Render the tool use message for ListMcpResourcesTool."""
    server = str((inputData or {}).get("server") or "")
    if server:
        return f'List MCP resources from server "{server}"'
    return "List all MCP resources"


def renderToolResultMessage(
    output: Any,
    progressMessages: Optional[list[dict[str, Any]]] = None,
    options: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """Render the tool result message for ListMcpResourcesTool."""
    del progressMessages, options
    if not output:
        return "(No resources found)"
    if isinstance(output, list) and len(output) == 0:
        return "(No resources found)"
    try:
        return json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True)
    except TypeError:
        return str(output)

def renderToolUseErrorMessage(errorMessage: str) -> str:
    """Render an error message for ListMcpResourcesTool."""
    return f"MCP resources error: {errorMessage}"
