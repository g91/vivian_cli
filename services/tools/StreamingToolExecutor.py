"""Streaming tool executor — mirrors src/services/tools/StreamingToolExecutor.ts."""
from __future__ import annotations

import asyncio
from typing import AsyncIterator, Optional


class StreamingToolExecutor:
    """Executes tools in streaming mode.

    Mirrors StreamingToolExecutor from StreamingToolExecutor.ts.
    """

    def __init__(self, tools: list, context: dict):
        self._tools = tools
        self._context = context

    async def execute(
        self,
        tool_name: str,
        tool_input: dict,
        tool_id: str,
        signal: Optional[asyncio.Event] = None,
    ) -> dict:
        from .toolExecution import executeToolCall
        return await executeToolCall(
            tool_name=tool_name,
            tool_input=tool_input,
            tool_id=tool_id,
            tools=self._tools,
            context=self._context,
            signal=signal,
        )
