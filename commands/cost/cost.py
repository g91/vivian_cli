"""cost command — mirrors src/commands/cost/cost.ts.

Shows session token usage and estimated cost.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult

# Approximate pricing per 1M tokens (USD)
MODEL_PRICING = {
    "qwen3.6": (0.15, 0.60),  # input, output
    "qwen3": (0.10, 0.40),
    "qwen2.5": (0.10, 0.40),
    "gemma4": (0.10, 0.40),
    "deepseek": (0.14, 0.28),
    "default": (0.15, 0.60),
}


def formatCost(
    input_tokens: int = 0,
    output_tokens: int = 0,
    model: str = "",
    total_cost: float = 0.0,
) -> str:
    """Format cost information."""
    total = input_tokens + output_tokens
    lines = [
        "╔══════════════════════════════════╗",
        "║        Session Cost              ║",
        "╚══════════════════════════════════╝",
        "",
        f"  Model:          {model or 'unknown'}",
        f"  Input tokens:   {input_tokens:,}",
        f"  Output tokens:  {output_tokens:,}",
        f"  Total tokens:   {total:,}",
        f"  Est. cost:      ${total_cost:.6f}",
    ]
    return "\n".join(lines)


async def call(args: str, context: CommandContext) -> TextResult:
    """Show session cost."""
    from ...types.command import TextResult

    in_tok = out_tok = 0
    model = ""
    cost = 0.0

    try:
        qe = getattr(context, "query_engine", None)
        if qe:
            in_tok = getattr(qe, "total_input_tokens", 0) or 0
            out_tok = getattr(qe, "total_output_tokens", 0) or 0
            model = getattr(qe, "model", "") or ""
    except Exception:
        pass

    try:
        ct = getattr(context, "cost_tracker", None)
        if ct:
            cost = getattr(ct, "total_cost", 0.0) or 0.0
    except Exception:
        pass

    return TextResult(formatCost(in_tok, out_tok, model, cost))


format_cost = formatCost
