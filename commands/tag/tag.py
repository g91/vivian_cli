"""tag command — mirrors src/commands/tag/tag.tsx.

Tag the current session for easier retrieval later.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


async def call(args: str, context: CommandContext) -> TextResult:
    from ...types.command import TextResult
    tag = args.strip() if args else ""
    if not tag:
        try:
            tags = getattr(context, "config", {}).get("session_tags", [])
            if tags:
                return TextResult(f"Session tags: {', '.join(tags)}")
        except Exception:
            pass
        return TextResult("Usage: /tag <name>")
    try:
        tags = list(getattr(context, "config", {}).get("session_tags", []))
        if tag not in tags:
            tags.append(tag)
            if hasattr(context, "set_setting"):
                context.set_setting("session_tags", tags)
    except Exception:
        pass
    return TextResult(f"Session tagged: {tag}")


tagSession = call
tag_session = call
