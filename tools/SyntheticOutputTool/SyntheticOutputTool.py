"""SyntheticOutputTool — mirrors src/tools/SyntheticOutputTool/SyntheticOutputTool.tsx"""
from __future__ import annotations
from typing import Any, Dict

TOOL_NAME = "SyntheticOutput"

INPUT_SCHEMA = {
    "type": "object",
    "required": ["content"],
    "properties": {
        "content": {"type": "string", "description": "Synthetic content to output"},
        "role": {"type": "string", "enum": ["assistant", "user"], "default": "assistant"},
    },
}


async def description() -> str:
    return "Inject synthetic content into the conversation."


async def prompt() -> str:
    return "Use this tool to inject synthetic messages into the conversation for testing or scaffolding."


async def call(input_data: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    return {
        "content": input_data.get("content", ""),
        "role": input_data.get("role", "assistant"),
    }
