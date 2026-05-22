"""LSPTool formatters — mirrors src/tools/LSPTool/formatters.ts"""
from typing import Any, Dict, List, Optional

def formatSymbolInfo(symbol: Dict[str, Any]) -> str:
    """Format a symbol's information for display."""
    name = symbol.get("name", "unknown")
    kind = symbol.get("kind", "")
    location = symbol.get("location", "")
    return f"{kind} {name} at {location}"

def formatDiagnostic(diagnostic: Dict[str, Any]) -> str:
    """Format a diagnostic message for display."""
    severity = diagnostic.get("severity", "info")
    message = diagnostic.get("message", "")
    location = diagnostic.get("location", "")
    return f"[{severity}] {location}: {message}"

def formatCompletionItem(item: Dict[str, Any]) -> str:
    """Format a completion item for display."""
    label = item.get("label", "")
    detail = item.get("detail", "")
    if detail:
        return f"{label} — {detail}"
    return label
