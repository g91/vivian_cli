"""env command — mirrors src/commands/env/.

Show current environment variables (sanitized).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


async def call(args: str, context: CommandContext) -> TextResult:
    from ...types.command import TextResult
    import os
    filter_key = args.strip().upper() if args else ""
    lines = ["Environment:", ""]
    sensitive = {"API_KEY", "TOKEN", "SECRET", "PASSWORD", "KEY"}
    for key in sorted(os.environ):
        if filter_key and filter_key not in key.upper():
            continue
        val = os.environ[key]
        if any(s in key.upper() for s in sensitive):
            val = val[:4] + "..." if len(val) > 4 else "***"
        elif len(val) > 80:
            val = val[:77] + "..."
        lines.append(f"  {key}={val}")
    return TextResult("\n".join(lines[:30]))


showEnv = call
show_env = call
