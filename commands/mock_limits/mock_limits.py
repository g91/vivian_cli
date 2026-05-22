"""mock-limits command — mirrors src/commands/mock-limits/.

Mock rate limit responses for testing limit handling.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


async def call(args: str, context: CommandContext) -> TextResult:
    from ...types.command import TextResult
    scenario = args.strip().lower() if args else ""
    if not scenario:
        return TextResult("Usage: /mock-limits <scenario>\nScenarios: rate_limit, quota_exceeded, timeout, off")
    if scenario == "off":
        return TextResult("Mock limits: OFF.")
    return TextResult(f"Mock limits set to: {scenario}")


setMockLimits = call
set_mock_limits = call
