"""LSPTool UI — mirrors src/tools/LSPTool/UI.tsx"""

from __future__ import annotations

from typing import Any, Dict, Optional

from ...utils.file import getDisplayPath


_OPERATION_LABELS = {
    "goToDefinition": ("definition", "definitions", None),
    "definition": ("definition", "definitions", None),
    "findReferences": ("reference", "references", None),
    "references": ("reference", "references", None),
    "documentSymbol": ("symbol", "symbols", None),
    "workspaceSymbol": ("symbol", "symbols", None),
    "hover": ("hover info", "hover info", "available"),
    "goToImplementation": ("implementation", "implementations", None),
    "completion": ("completion", "completions", None),
    "diagnostics": ("diagnostic", "diagnostics", None),
}


def userFacingName() -> str:
    return "LSP"


def renderToolUseMessage(inputData: Dict[str, Any], options: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """Render the tool use message for LSPTool."""
    operation = inputData.get("action") or inputData.get("operation")
    if not operation:
        return None

    verbose = bool((options or {}).get("verbose"))
    file_path = inputData.get("file_path") or inputData.get("filePath")
    display_path = str(file_path or "")
    if display_path and not verbose:
        display_path = getDisplayPath(display_path)

    parts = [f'operation: "{operation}"']
    if display_path:
        parts.append(f'file: "{display_path}"')

    line = inputData.get("line")
    character = inputData.get("character")
    if line is not None and character is not None:
        parts.append(f"position: {line}:{character}")
    return ", ".join(parts)

def renderToolResultMessage(output: Dict[str, Any]) -> Optional[str]:
    """Render the tool result message for LSPTool."""
    if "error" in output:
        return f"LSP error: {output['error']}"

    result_count = output.get("resultCount")
    file_count = output.get("fileCount")
    operation = str(output.get("operation") or output.get("action") or "")
    if isinstance(result_count, int) and isinstance(file_count, int):
        singular, plural, special = _OPERATION_LABELS.get(operation, ("result", "results", None))
        if operation == "hover" and result_count > 0 and special:
            summary = f"Hover info {special}"
        else:
            label = singular if result_count == 1 else plural
            summary = f"Found {result_count} {label}"
        if file_count > 1:
            summary += f" across {file_count} files"
        return summary

    result = output.get("result", {})
    if isinstance(result, list):
        if not result:
            return "No results."
        lines = []
        for item in result[:20]:
            if isinstance(item, dict):
                lines.append(item.get("name", item.get("label", str(item))))
            else:
                lines.append(str(item))
        return "\n".join(lines)
    if isinstance(result, dict):
        return str(result)
    return str(result)

def renderToolUseErrorMessage(errorMessage: str) -> str:
    """Render an error message for LSPTool."""
    return f"LSP error: {errorMessage}"
