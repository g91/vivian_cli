"""config command — mirrors src/commands/config/config.tsx.

View or modify Vivian CLI configuration settings.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


def formatConfig(config: dict) -> str:
    """Format configuration for display."""
    lines = ["╔══════════════════════════════════╗",
             "║        Configuration             ║",
             "╚══════════════════════════════════╝", ""]
    for key, value in sorted(config.items()):
        if isinstance(value, dict):
            lines.append(f"  {key}:")
            for k, v in value.items():
                lines.append(f"    {k}: {v}")
        else:
            lines.append(f"  {key}: {value}")
    return "\n".join(lines)


async def call(args: str, context: CommandContext) -> TextResult:
    """View or modify configuration."""
    from ...types.command import TextResult

    parts = args.strip().split(maxsplit=1) if args.strip() else []
    key = parts[0] if parts else ""
    val = parts[1] if len(parts) > 1 else None

    cfg = {}
    try:
        cfg = getattr(context, "config", {}) or {}
    except Exception:
        pass

    if not key:
        return TextResult(formatConfig(cfg))

    if val is not None:
        try:
            if hasattr(context, "set_setting"):
                context.set_setting(key, val)
            cfg[key] = val
        except Exception as e:
            return TextResult(f"Error setting {key}: {e}")
        return TextResult(f"Set {key} = {val}")

    # Show specific key
    current = cfg.get(key, "<not set>")
    return TextResult(f"{key} = {current}")


format_config = formatConfig
