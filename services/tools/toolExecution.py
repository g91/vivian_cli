"""Tool execution — mirrors src/services/tools/toolExecution.ts."""
from __future__ import annotations

import asyncio
from typing import Any, Callable, Optional

from ...utils.toolResultStorage import (
    DEFAULT_MAX_RESULT_SIZE_CHARS,
    processPreMappedToolResultBlock,
)


async def _normalize_tool_result_content(tool_name: str, tool_id: str, result: Any) -> str:
    raw_content = result if isinstance(result, str) else str(result)
    processed_block = await processPreMappedToolResultBlock(
        {
            "type": "tool_result",
            "tool_use_id": tool_id,
            "content": raw_content,
        },
        tool_name,
        DEFAULT_MAX_RESULT_SIZE_CHARS,
    )
    if isinstance(processed_block, dict) and processed_block.get("content") is not None:
        return str(processed_block["content"])
    return raw_content


async def executeToolCall(
    tool_name: str,
    tool_input: dict,
    tool_id: str,
    tools: list,
    context: dict,
    signal: Optional[asyncio.Event] = None,
    can_use_tool: Optional[Callable] = None,
) -> dict:
    """Execute a single tool call.

    Mirrors executeToolCall() from toolExecution.ts.
    """
    tool = next((t for t in tools if t.get("name") == tool_name), None)
    if not tool:
        return {
            "type": "tool_result",
            "tool_use_id": tool_id,
            "content": f"Tool '{tool_name}' not found",
            "is_error": True,
        }
    try:
        run_fn = tool.get("run")
        if run_fn:
            result = await run_fn(tool_input, context)
        else:
            result = {"error": "Tool has no run function"}
        content = await _normalize_tool_result_content(tool_name, tool_id, result)
        return {
            "type": "tool_result",
            "tool_use_id": tool_id,
            "content": content,
            "is_error": isinstance(result, dict) and "error" in result,
        }
    except Exception as e:
        return {
            "type": "tool_result",
            "tool_use_id": tool_id,
            "content": str(e),
            "is_error": True,
        }


execute_tool_call = executeToolCall
