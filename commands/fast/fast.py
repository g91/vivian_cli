"""fast command — mirrors src/commands/fast/fast.tsx.

Toggle fast mode for quicker, lower-cost responses.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


def fastModeMessage(enabled: bool) -> str:
    return f"Fast mode: {'ON' if enabled else 'OFF'}"


async def call(args: str, context: CommandContext) -> TextResult:
    from ...types.command import TextResult
    current = bool(getattr(context, "fast_mode", False))
    try:
        if not current:
            current = getattr(context, "config", {}).get("fast_mode", False)
    except Exception:
        pass
    new_state = not current

    try:
        setattr(context, "fast_mode", new_state)
    except Exception:
        pass

    try:
        tui = getattr(context, "_tui", None)
        if tui is not None and hasattr(tui, "toggle_fast"):
            tui.toggle_fast()
    except Exception:
        pass

    try:
        if hasattr(context, "set_setting"):
            context.set_setting("fast_mode", new_state)
    except Exception:
        pass

    return TextResult(fastModeMessage(new_state))


fast_mode_message = fastModeMessage
