"""BriefTool — mirrors src/tools/BriefTool/BriefTool.tsx"""
from __future__ import annotations
from typing import Any, Dict, Optional

TOOL_NAME = "Brief"

INPUT_SCHEMA = {
    "type": "object",
    "required": ["content"],
    "properties": {
        "content": {"type": "string", "description": "The content for the brief"},
        "title": {"type": "string", "description": "Optional title for the brief"},
    },
}


async def description() -> str:
    return "Compose a brief or summary document."


async def prompt() -> str:
    return (
        "Use this tool to write a brief, memo, or summary to share with the user. "
        "The content will be rendered as markdown."
    )


async def call(input_data: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    content = input_data.get("content", "")
    title = input_data.get("title")
    output = f"# {title}\n\n{content}" if title else content
    return {"output": output}
