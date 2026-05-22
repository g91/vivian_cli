"""token-count command.

Estimate tokens in the current conversation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..services.tokenEstimation import roughTokenCountEstimationForMessages

if TYPE_CHECKING:
    from ..types.command import CommandContext, TextResult


def _message_dict(message: Any) -> dict:
    if isinstance(message, dict):
        return {
            "role": message.get("role"),
            "content": message.get("content"),
        }
    return {
        "role": getattr(message, "role", None),
        "content": getattr(message, "content", None),
    }


async def call(args: str, context: CommandContext) -> TextResult:
    del args
    from ..types.command import TextResult

    try:
        engine = getattr(context, "engine", None)
        if engine is None:
            engine = getattr(context, "query_engine", None)
        messages = []
        if engine is not None:
            if hasattr(engine, "get_messages"):
                messages = engine.get_messages()
            else:
                messages = getattr(engine, "messages", []) or []
        msg_dicts = [_message_dict(message) for message in messages]
        estimate = roughTokenCountEstimationForMessages(msg_dicts)
        return TextResult(f"Estimated tokens: {estimate:,}\nMessages: {len(messages)}")
    except Exception as exc:
        return TextResult(f"Token count unavailable: {exc}")
