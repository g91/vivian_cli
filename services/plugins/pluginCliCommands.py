"""Plugin CLI commands — mirrors src/services/plugins/pluginCliCommands.ts."""
from __future__ import annotations

import asyncio


async def installPlugin(name: str, scope: str = "user") -> None:
    """Install a plugin by name.

    Mirrors installPlugin() from pluginCliCommands.ts.
    """
    from ...cli.handlers.plugins import install_plugin_handler

    await asyncio.to_thread(install_plugin_handler, name, scope)


async def uninstallPlugin(name: str, scope: str = "user") -> None:
    """Uninstall a plugin by name.

    Mirrors uninstallPlugin() from pluginCliCommands.ts.
    """
    del scope
    from ...cli.handlers.plugins import uninstall_plugin_handler

    await asyncio.to_thread(uninstall_plugin_handler, name)


async def enablePlugin(name: str, scope: str = "user") -> None:
    """Enable a plugin by name.

    Mirrors enablePlugin() from pluginCliCommands.ts.
    """
    del scope
    from ...cli.handlers.plugins import enable_plugin_handler

    await asyncio.to_thread(enable_plugin_handler, name)


async def disablePlugin(name: str, scope: str = "user") -> None:
    """Disable a plugin by name.

    Mirrors disablePlugin() from pluginCliCommands.ts.
    """
    del scope
    from ...cli.handlers.plugins import disable_plugin_handler

    await asyncio.to_thread(disable_plugin_handler, name)


VALID_INSTALLABLE_SCOPES = frozenset({"user", "project"})
VALID_UPDATE_SCOPES = frozenset({"user", "project"})

install_plugin = installPlugin
uninstall_plugin = uninstallPlugin
enable_plugin = enablePlugin
disable_plugin = disablePlugin
