"""MCPTool UI — mirrors src/tools/MCPTool/UI.tsx."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional


MAX_INPUT_VALUE_CHARS = 80
MAX_RESULT_CHARS = 2000


def _json_stringify(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    except TypeError:
        return str(value)


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def _flatten_mcp_result(result: Any) -> str:
    if result is None:
        return "(No content)"
    if isinstance(result, str):
        return _truncate(result, MAX_RESULT_CHARS)
    if isinstance(result, list):
        lines: list[str] = []
        for item in result:
            if isinstance(item, dict):
                item_type = item.get("type")
                if item_type == "image":
                    lines.append("[Image]")
                    continue
                if item_type == "text" and item.get("text") is not None:
                    lines.append(str(item.get("text")))
                    continue
            lines.append(_json_stringify(item))
        joined = "\n".join(line for line in lines if line)
        return _truncate(joined or "(No content)", MAX_RESULT_CHARS)
    if isinstance(result, dict):
        if "text" in result and isinstance(result.get("text"), str):
            return _truncate(str(result["text"]), MAX_RESULT_CHARS)
        return _truncate(_json_stringify(result), MAX_RESULT_CHARS)
    return _truncate(str(result), MAX_RESULT_CHARS)


def renderToolUseMessage(inputData: Dict[str, Any], options: Optional[Dict[str, Any]] = None) -> str:
    """Render the tool use message for MCPTool."""
    if not inputData:
        return ""
    verbose = bool((options or {}).get("verbose", False))
    parts: list[str] = []
    for key, value in inputData.items():
        rendered = _json_stringify(value)
        if not verbose:
            rendered = _truncate(rendered, MAX_INPUT_VALUE_CHARS)
        parts.append(f"{key}: {rendered}")
    return ", ".join(parts)


def renderToolResultMessage(
    output: Dict[str, Any] | str,
    progressMessages: Optional[list[dict[str, Any]]] = None,
    options: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """Render the tool result message for MCPTool."""
    del progressMessages, options
    if isinstance(output, str):
        return _truncate(output, MAX_RESULT_CHARS)
    if output.get("error"):
        return f"MCP error: {output['error']}"
    return _flatten_mcp_result(output.get("result"))


def renderToolUseErrorMessage(errorMessage: str) -> str:
    """Render an error message for MCPTool."""
    return f"MCP error: {errorMessage}"
