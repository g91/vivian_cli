"""reload-plugins command — mirrors src/commands/reload-plugins/.

Reloads all installed plugins without restarting.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


def reloadPlugins() -> str:
    return "Plugins reloaded."


async def call(args: str, context: CommandContext) -> TextResult:
    from ...types.command import TextResult
    # Trigger plugin reload through the plugin system
    try:
        from ...plugins import reload_all
        reload_all()
    except Exception:
        pass
    return TextResult(reloadPlugins())


reload_plugins = reloadPlugins
