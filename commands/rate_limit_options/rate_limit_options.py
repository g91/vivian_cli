"""rate-limit-options command — mirrors src/commands/rate-limit-options/.

Configure rate limit and quota options for API usage.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


async def call(args: str, context: CommandContext) -> TextResult:
    """View or configure rate limit options."""
    from ...types.command import TextResult
    parts = args.strip().split() if args.strip() else []
    action = parts[0].lower() if parts else ""

    if not action:
        return TextResult(
            "Rate Limit Options:\n"
            "  Tier: Standard (local Ollama — no rate limits)\n"
            "  Max tokens/request: 128K\n"
            "  Concurrent requests: 1\n"
            "\nUse /rate-limit-options tokens <n> to adjust."
        )

    if action == "tokens" and len(parts) >= 2:
        try:
            n = int(parts[1])
            if hasattr(context, "set_setting"):
                context.set_setting("max_tokens", n)
            return TextResult(f"Max tokens per request set to: {n}")
        except ValueError:
            return TextResult(f"Invalid number: {parts[1]}")

    return TextResult("Usage: /rate-limit-options [tokens <n>]")


showRateLimitOptions = call
show_rate_limit_options = call
