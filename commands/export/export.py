"""export command — mirrors src/commands/export/export.tsx.

Export the conversation as JSON or Markdown.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


def _message_field(message, field: str) -> str:
    if isinstance(message, dict):
        return str(message.get(field, "") or "")
    return str(getattr(message, field, "") or "")


def exportConversation(messages: list) -> str:
    """Export conversation as JSON."""
    export = []
    for m in messages:
        export.append({
            "role": _message_field(m, "role"),
            "content": _message_field(m, "content"),
        })
    return json.dumps(export, indent=2)


async def call(args: str, context: CommandContext) -> TextResult:
    """Export the conversation."""
    from ...types.command import TextResult
    fmt = args.strip().lower() if args else "json"
    try:
        qe = getattr(context, "query_engine", None)
        if qe:
            msgs = getattr(qe, "messages", []) or []
            if fmt == "json":
                return TextResult(exportConversation(msgs))
            elif fmt == "md":
                lines = ["# Conversation Export\n"]
                for m in msgs:
                    role = _message_field(m, "role")
                    content = _message_field(m, "content")
                    lines.append(f"## {role}\n\n{content}\n")
                return TextResult("\n".join(lines))
    except Exception:
        pass
    return TextResult("No conversation to export.")


export_conversation = exportConversation
