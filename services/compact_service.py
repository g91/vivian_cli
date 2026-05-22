"""Compact service — manages context window compaction.

Mirrors src/services/compact/.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from ..types import Message
from ..api.client import VivianClient

logger = logging.getLogger(__name__)


class CompactService:
    """Manages conversation compaction to stay within context limits."""

    # Approximate token limits
    DEFAULT_MAX_CONTEXT_TOKENS = 100000
    COMPACT_TRIGGER_RATIO = 0.75  # Compact at 75% of max

    def __init__(self, max_context_tokens: int = DEFAULT_MAX_CONTEXT_TOKENS):
        self.max_context_tokens = max_context_tokens
        self.compact_count = 0

    def estimate_tokens(self, messages: list[Message]) -> int:
        """Rough token estimation: ~4 chars per token."""
        total = 0
        for m in messages:
            if m.content:
                total += len(m.content) // 4
            if m.tool_calls:
                total += len(str(m.tool_calls)) // 4
        return total

    def should_compact(self, messages: list[Message]) -> bool:
        """Check if compaction is needed."""
        tokens = self.estimate_tokens(messages)
        return tokens > self.max_context_tokens * self.COMPACT_TRIGGER_RATIO

    async def compact(
        self,
        messages: list[Message],
        client: VivianClient,
        model: str,
    ) -> list[Message]:
        """Compact the conversation by summarizing early messages.

        Keeps the first few messages (system context) and last N messages,
        replacing the middle with a summary.
        """
        self.compact_count += 1
        logger.info(f"Compacting conversation (count={self.compact_count})")

        if len(messages) <= 10:
            return messages

        # Keep first 2 and last 8 messages
        keep_head = 2
        keep_tail = 8
        middle = messages[keep_head:-keep_tail]

        if not middle:
            return messages

        # Generate summary of middle messages
        summary_text = "Previous conversation summary:\n"
        for m in middle:
            if m.role == "user" and m.content:
                summary_text += f"User: {m.content[:200]}...\n"
            elif m.role == "assistant" and m.content:
                summary_text += f"Assistant: {m.content[:200]}...\n"

        summary_msg = Message(role="system", content=summary_text)

        return [
            messages[0],
            summary_msg,
            *messages[-keep_tail:],
        ]

    def micro_compact(
        self, messages: list[Message], max_messages: int = 50
    ) -> list[Message]:
        """Light compaction: just trim oldest messages."""
        if len(messages) <= max_messages:
            return messages
        return messages[-max_messages:]
