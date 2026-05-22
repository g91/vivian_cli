"""REPL primitive tools — mirrors src/tools/REPLTool/primitiveTools.ts"""
from typing import Any, Dict, List

PRIMITIVE_TOOLS: Dict[str, Dict[str, Any]] = {
    "python": {
        "name": "Python REPL",
        "language": "python",
        "description": "Execute Python code interactively",
    },
    "javascript": {
        "name": "JavaScript REPL",
        "language": "javascript",
        "description": "Execute JavaScript code interactively",
    },
    "bash": {
        "name": "Bash REPL",
        "language": "bash",
        "description": "Execute bash commands interactively",
    },
}

def getPrimitiveTool(language: str) -> Dict[str, Any]:
    """Get a primitive tool definition by language."""
    return PRIMITIVE_TOOLS.get(language, {})

def listPrimitiveTools() -> List[str]:
    """List all available primitive tool languages."""
    return list(PRIMITIVE_TOOLS.keys())
