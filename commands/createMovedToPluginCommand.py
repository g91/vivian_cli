"""Create moved-to-plugin command — mirrors src/commands/createMovedToPluginCommand.ts."""
from __future__ import annotations

import os
from collections.abc import Awaitable, Callable
from typing import Any

from ..types.command import PromptCommand


def createMovedToPluginCommand(
    *,
    name: str,
    description: str,
    progressMessage: str,
    pluginName: str,
    pluginCommand: str,
    getPromptWhileMarketplaceIsPrivate: Callable[[str, Any], Awaitable[list[dict[str, str]]]],
) -> PromptCommand:
    """Create a prompt command that redirects users to the plugin marketplace."""

    async def _get_prompt_for_command(args: str = "", context: Any = None) -> list[dict[str, str]]:
        if os.environ.get("USER_TYPE") == "ant":
            return [
                {
                    "type": "text",
                    "text": (
                        "This command has been moved to a plugin. Tell the user:\n\n"
                        "1. To install the plugin, run:\n"
                        f"   vivian plugin install {pluginName}@vivian-code-marketplace\n\n"
                        f"2. After installation, use /{pluginName}:{pluginCommand} to run this command\n\n"
                        "3. For more information, see: "
                        f"https://github.com/anthropics/vivian-code-marketplace/blob/main/{pluginName}/README.md\n\n"
                        "Do not attempt to run the command. Simply inform the user about the plugin installation."
                    ),
                }
            ]
        return await getPromptWhileMarketplaceIsPrivate(args, context)

    return PromptCommand(
        progress_message=progressMessage,
        content_length=0,
        get_prompt_for_command=_get_prompt_for_command,
        source="builtin",
    )


create_moved_to_plugin_command = createMovedToPluginCommand
