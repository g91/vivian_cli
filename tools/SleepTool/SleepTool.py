"""SleepTool — mirrors src/tools/SleepTool/SleepTool.tsx"""
from __future__ import annotations
import asyncio
from typing import Any, Dict

TOOL_NAME = "Sleep"

INPUT_SCHEMA = {
    "type": "object",
    "required": ["duration"],
    "properties": {
        "duration": {"type": "number", "description": "Duration to sleep in milliseconds"},
    },
}


async def description() -> str:
    return "Sleep for a specified duration."


async def prompt() -> str:
    return (
        "Use this tool to pause execution for a specified duration (in milliseconds). "
        "Useful for rate limiting or waiting for async operations to complete."
    )


async def call(input_data: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    duration_ms = input_data.get("duration", 0)
    await asyncio.sleep(duration_ms / 1000)
    return {"slept": True, "duration": duration_ms}
