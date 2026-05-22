"""
Port of src/utils/plugins/pluginBlocklist.ts

Plugin delisting detection.
"""
from __future__ import annotations

from typing import Any, Dict, List

from ..debug import logForDebugging
from ..errors import errorMessage
from .installedPluginsManager import loadInstalledPluginsV2
from .marketplaceManager import getMarketplace, loadKnownMarketplacesConfigSafe
from .pluginFlagging import addFlaggedPlugin, getFlaggedPlugins, loadFlaggedPlugins


def detectDelistedPlugins(
    installed_plugins: Dict[str, Any],
    marketplace: Dict[str, Any],
    marketplace_name: str,
) -> List[str]:
    """Detect plugins installed from a marketplace that are no longer listed there."""
    marketplace_plugin_names = {p.get("name") for p in marketplace.get("plugins", [])}
    suffix = f"@{marketplace_name}"

    delisted: List[str] = []
    for plugin_id in installed_plugins.get("plugins", {}):
        if not plugin_id.endswith(suffix):
            continue
        plugin_name = plugin_id[:-len(suffix)]
        if plugin_name not in marketplace_plugin_names:
            delisted.append(plugin_id)

    return delisted


async def detectAndUninstallDelistedPlugins() -> List[str]:
    """Detect delisted plugins across all marketplaces, auto-uninstall them."""
    await loadFlaggedPlugins()

    installed_plugins = loadInstalledPluginsV2()
    already_flagged = getFlaggedPlugins()
    known_marketplaces = await loadKnownMarketplacesConfigSafe()
    newly_flagged: List[str] = []

    for marketplace_name in known_marketplaces:
        try:
            marketplace = await getMarketplace(marketplace_name)
            if not marketplace.get("forceRemoveDeletedPlugins"):
                continue

            delisted = detectDelistedPlugins(installed_plugins, marketplace, marketplace_name)

            for plugin_id in delisted:
                if plugin_id in already_flagged:
                    continue

                installations = installed_plugins.get("plugins", {}).get(plugin_id, [])
                has_user_install = any(
                    i.get("scope") in ("user", "project", "local")
                    for i in installations
                )
                if not has_user_install:
                    continue

                for installation in installations:
                    scope = installation.get("scope")
                    if scope not in ("user", "project", "local"):
                        continue
                    try:
                        from ...services.plugins.pluginOperations import uninstallPluginOp
                        await uninstallPluginOp(plugin_id, scope)
                    except Exception as e:
                        logForDebugging(
                            f"Failed to auto-uninstall delisted plugin {plugin_id} from {scope}: {errorMessage(e)}",
                            level="error",
                        )

                await addFlaggedPlugin(plugin_id)
                newly_flagged.append(plugin_id)
        except Exception as e:
            logForDebugging(
                f'Failed to check for delisted plugins in "{marketplace_name}": {errorMessage(e)}',
                level="warn",
            )

    return newly_flagged

