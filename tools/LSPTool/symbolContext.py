"""LSPTool symbol context — mirrors src/tools/LSPTool/symbolContext.ts"""
from typing import Any, Dict, List, Optional

def getSymbolContext(
    filePath: str,
    line: int,
    character: int,
) -> Dict[str, Any]:
    """Get context about the symbol at a given position."""
    return {
        "filePath": filePath,
        "line": line,
        "character": character,
        "symbols": [],
        "diagnostics": [],
    }

def findEnclosingSymbol(
    symbols: List[Dict[str, Any]],
    line: int,
    character: int,
) -> Optional[Dict[str, Any]]:
    """Find the symbol that encloses the given position."""
    for symbol in symbols:
        startLine = symbol.get("startLine", 0)
        endLine = symbol.get("endLine", 0)
        if startLine <= line <= endLine:
            return symbol
    return None
