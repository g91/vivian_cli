"""vim command — mirrors src/commands/vim/vim.ts.

Toggle VIM-style keybindings for the input area.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...services.analytics.index import log_event
from ...utils.config import get_global_config, save_global_config

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


def toggleVimMessage(enabled: bool) -> str:
    """Get vim toggle message."""
    if enabled:
        return "Editor mode set to vim. Use Escape key to toggle between INSERT and NORMAL modes."
    return "Editor mode set to normal. Using standard (readline) keyboard bindings."


async def call(args: str, context: CommandContext) -> TextResult:
    """Toggle VIM mode."""
    from ...types.command import TextResult

    current_enabled = bool(getattr(context, "_vim_enabled", False))
    if not current_enabled:
        config = get_global_config()
        current_mode = config.get("editorMode") or "normal"
        if current_mode == "emacs":
            current_mode = "normal"
        current_enabled = current_mode == "vim"

    new_mode = "normal" if current_enabled else "vim"

    try:
        setattr(context, "_vim_enabled", new_mode == "vim")
    except Exception:
        pass

    try:
        tui = getattr(context, "_tui", None)
        if tui is not None and hasattr(tui, "toggle_vim"):
            tui.toggle_vim()
    except Exception:
        pass

    save_global_config(lambda current: {**current, "editorMode": new_mode})
    log_event("tengu_editor_mode_changed", {"mode": new_mode, "source": "command"})
    return TextResult(toggleVimMessage(new_mode == "vim"))


toggle_vim_message = toggleVimMessage
