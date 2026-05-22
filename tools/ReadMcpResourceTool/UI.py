"""ReadMcpResourceTool UI — mirrors src/tools/ReadMcpResourceTool/UI.tsx."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional


def renderToolUseMessage(inputData: Dict[str, Any]) -> Optional[str]:
    """Render the tool use message for ReadMcpResourceTool."""
    uri = str(inputData.get("uri") or "")
    server = str(inputData.get("server") or "")
    if not uri or not server:
        return None
    return f'Read resource "{uri}" from server "{server}"'


def userFacingName() -> str:
    return "readMcpResource"


def renderToolResultMessage(
    output: Dict[str, Any],
    progressMessages: Optional[list[dict[str, Any]]] = None,
    options: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """Render the tool result message for ReadMcpResourceTool."""
    del progressMessages, options
    if output.get("error"):
        return f"MCP resource error: {output['error']}"
    contents = output.get("contents")
    if not contents:
        return "(No content)"
    try:
        return json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True)
    except TypeError:
        return str(output)

def renderToolUseErrorMessage(errorMessage: str) -> str:
    """Render an error message for ReadMcpResourceTool."""
    return f"Read MCP resource error: {errorMessage}"
