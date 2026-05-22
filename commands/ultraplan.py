"""ultraplan command — mirrors src/commands/ultraplan.tsx.

Deep multi-agent planning mode for complex tasks (10-30 min analysis).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..types.command import CommandContext, TextResult


def ultraplanMode(enabled: bool) -> str:
    return f"Ultraplan mode: {'ON' if enabled else 'OFF'}"


async def call(args: str, context: CommandContext) -> TextResult:
    """Launch ultraplan for a complex task."""
    from ..types.command import TextResult
    prompt = args.strip() if args else ""
    if not prompt:
        return TextResult("Usage: /ultraplan <description of complex task>")
    plan_prompt = f"""You are an advanced planning agent. Create a comprehensive plan for:

{prompt}

Include:
1. **Goal Analysis** — What exactly needs to be accomplished?
2. **Architecture** — High-level design and component breakdown
3. **Implementation Steps** — Ordered, actionable steps
4. **Dependencies** — What needs to be in place first?
5. **Risk Assessment** — Potential pitfalls and mitigations
6. **Estimated Effort** — Time/complexity per step

Be thorough. This plan will guide implementation."""
    return TextResult(plan_prompt)


ultraplan_mode = ultraplanMode
