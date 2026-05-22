"""Tool orchestration — mirrors src/services/tools/toolOrchestration.ts."""
from __future__ import annotations

import asyncio
from typing import Callable, Optional


async def executeToolBatch(
    tool_uses: list[dict],
    tools: list,
    context: dict,
    signal: Optional[asyncio.Event] = None,
    can_use_tool: Optional[Callable] = None,
    on_progress: Optional[Callable] = None,
) -> list[dict]:
    """Execute a batch of tool calls.

    Mirrors executeToolBatch() from toolOrchestration.ts.
    """
    from .toolExecution import executeToolCall
    results = []
    for tool_use in tool_uses:
        result = await executeToolCall(
            tool_name=tool_use.get("name", ""),
            tool_input=tool_use.get("input", {}),
            tool_id=tool_use.get("id", ""),
            tools=tools,
            context=context,
            signal=signal,
            can_use_tool=can_use_tool,
        )
        results.append(result)
    return results


execute_tool_batch = executeToolBatch
