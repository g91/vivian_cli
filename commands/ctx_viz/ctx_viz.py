"""ctx-viz command — mirrors src/commands/ctx_viz/.

Visualize the current context window usage and token distribution.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


async def call(args: str, context: CommandContext) -> TextResult:
    from ...types.command import TextResult
    lines = ["Context Visualization:", ""]
    try:
        qe = getattr(context, "query_engine", None)
        if qe:
            msgs = getattr(qe, "messages", []) or []
            total_chars = sum(len(str(getattr(m, "content", ""))) for m in msgs)
            lines.append(f"  Total messages: {len(msgs)}")
            lines.append(f"  Total chars: {total_chars:,}")
            lines.append(f"  Est. tokens: ~{total_chars // 4:,}")
            roles: dict[str, int] = {}
            for m in msgs:
                r = getattr(m, "role", "unknown")
                roles[r] = roles.get(r, 0) + 1
            lines.append("  By role:")
            for role, count in sorted(roles.items()):
                bar = "█" * min(count, 40)
                lines.append(f"    {role:<12} {bar} {count}")
    except Exception:
        pass
    return TextResult("\n".join(lines))


visualizeContext = call
visualize_context = call
