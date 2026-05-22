"""LSPTool schemas — mirrors src/tools/LSPTool/schemas.ts"""
from typing import Any, Dict

LSP_INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["operation", "filePath"],
    "properties": {
        "operation": {
            "type": "string",
            "enum": ["definition", "references", "hover", "diagnostics", "completions", "symbols"],
            "description": "The LSP operation to perform",
        },
        "filePath": {
            "type": "string",
            "description": "The file path to operate on",
        },
        "line": {
            "type": "number",
            "description": "The line number (1-based)",
        },
        "character": {
            "type": "number",
            "description": "The character offset (1-based)",
        },
    },
}

LSP_OUTPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "result": {},
        "error": {"type": "string"},
    },
}
