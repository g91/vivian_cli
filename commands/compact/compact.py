"""compact command — mirrors src/commands/compact/compact.ts.

Compacts the conversation history to save tokens by summarizing earlier messages.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


async def compactConversation(messages: list, client, model: str) -> list:
    """Compact the conversation history."""
    from ...services.compact_service import CompactService
    service = CompactService()
    return await service.compact(messages, client, model)


async def call(args: str, context: CommandContext) -> TextResult:
    """Trigger conversation compaction."""
    from ...types.command import TextResult
    try:
        qe = getattr(context, "query_engine", None)
        if qe is None:
            qe = getattr(context, "engine", None)
        if qe and hasattr(qe, "messages"):
            msgs = list(getattr(qe, "messages", []) or [])
            if len(msgs) <= 10:
                return TextResult("Not enough messages to compact (need >10).")

            client = getattr(context, "client", None) or getattr(qe, "client", None)
            model = getattr(qe, "model", None) or getattr(context, "model", "")
            service = getattr(context, "compact_service", None)
            if service is None:
                from ...services.compact_service import CompactService

                service = CompactService()

            compacted = await service.compact(msgs, client, model)
            setattr(qe, "messages", compacted)
            return TextResult(f"Compacted from {len(msgs)} to {len(compacted)} messages")
    except Exception as e:
        return TextResult(f"Compaction failed: {e}")
    return TextResult("Not enough messages to compact (need >10).")


compact_conversation = compactConversation
