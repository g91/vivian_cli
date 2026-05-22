"""
Port of src/utils/plugins/pluginAutoupdate.ts

Background plugin autoupdate functionality.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Set

from ..config import shouldSkipPluginAutoupdate
from ..debug import logForDebugging
from ..errors import errorMessage
from ..log import logError
from .installedPluginsManager import (
    getPendingUpdatesDetails,
    hasPendingUpdates,
    isInstallationRelevantToCurrentProject,
    loadInstalledPluginsFromDisk,
)
from .marketplaceManager import (
    getDeclaredMarketplaces,
    loadKnownMarketplacesConfig,
    refreshMarketplace,
)
from .pluginIdentifier import parsePluginIdentifier
from .schemas import isMarketplaceAutoUpdate, PluginScope

PluginAutoUpdateCallback = Callable[[List[str]], None]

_plugin_update_callback: Optional[PluginAutoUpdateCallback] = None
_pending_notification: Optional[List[str]] = None


def onPluginsAutoUpdated(callback: PluginAutoUpdateCallback) -> Callable[[], None]:
    global _plugin_update_callback, _pending_notification
    _plugin_update_callback = callback
    if _pending_notification:
        callback(_pending_notification)
        _pending_notification = None
    return lambda: setattr(onPluginsAutoUpdated, "_plugin_update_callback", None)


def getAutoUpdatedPluginNames() -> List[str]:
    if not hasPendingUpdates():
        return []
    return [parsePluginIdentifier(d["pluginId"])["name"] for d in getPendingUpdatesDetails()]


async def _get_auto_update_enabled_marketplaces() -> Set[str]:
    config = await loadKnownMarketplacesConfig()
    declared = getDeclaredMarketplaces()
    enabled: Set[str] = set()
    for name, entry in config.items():
        declared_auto = declared.get(name, {}).get("autoUpdate")
        auto_update = declared_auto if declared_auto is not None else isMarketplaceAutoUpdate(name, entry)
        if auto_update:
            enabled.add(name.lower())
    return enabled


async def updatePluginsForMarketplaces(marketplace_names: Set[str]) -> List[str]:
    installed = loadInstalledPluginsFromDisk()
    plugin_ids = list(installed.get("plugins", {}).keys())
    if not plugin_ids:
        return []

    updated: List[str] = []
    for plugin_id in plugin_ids:
        parsed = parsePluginIdentifier(plugin_id)
        marketplace = parsed.get("marketplace", "")
        if not marketplace or marketplace.lower() not in marketplace_names:
            continue
        installations = installed["plugins"].get(plugin_id, [])
        relevant = [i for i in installations if isInstallationRelevantToCurrentProject(i)]
        if not relevant:
            continue
        try:
            from ...services.plugins.pluginOperations import updatePluginOp
            for inst in relevant:
                result = await updatePluginOp(plugin_id, inst.get("scope", "user"))
                if result.get("success") and not result.get("alreadyUpToDate"):
                    updated.append(plugin_id)
        except Exception as e:
            logForDebugging(f"Plugin autoupdate: error updating {plugin_id}: {errorMessage(e)}", level="warn")
    return updated


def autoUpdateMarketplacesAndPluginsInBackground() -> None:
    import asyncio

    async def _run() -> None:
        global _plugin_update_callback, _pending_notification
        if shouldSkipPluginAutoupdate():
            logForDebugging("Plugin autoupdate: skipped")
            return
        try:
            auto_markets = await _get_auto_update_enabled_marketplaces()
            if not auto_markets:
                return
            for name in auto_markets:
                try:
                    await refreshMarketplace(name, options={"disableCredentialHelper": True})
                except Exception as e:
                    logForDebugging(f"Plugin autoupdate: failed to refresh {name}: {errorMessage(e)}", level="warn")

            updated = await updatePluginsForMarketplaces(auto_markets)
            if updated:
                if _plugin_update_callback:
                    _plugin_update_callback(updated)
                else:
                    _pending_notification = updated
        except Exception as e:
            logError(e)

    asyncio.ensure_future(_run())


async def getAutoUpdateEnabledMarketplaces() -> Set[str]:
    return await _get_auto_update_enabled_marketplaces()


async def updatePlugin(plugin_id: str, installations: Optional[List[Dict[str, Any]]] = None) -> Optional[str]:
    installed = loadInstalledPluginsFromDisk()
    candidate_installations = installations if installations is not None else installed.get("plugins", {}).get(plugin_id, [])
    parsed = parsePluginIdentifier(plugin_id)
    marketplace = parsed.get("marketplace", "")
    if not marketplace or not candidate_installations:
        return None
    updated = await updatePluginsForMarketplaces({marketplace.lower()})
    return plugin_id if plugin_id in updated else None


async def updatePlugins(auto_update_enabled_marketplaces: Set[str]) -> List[str]:
    return await updatePluginsForMarketplaces(auto_update_enabled_marketplaces)

