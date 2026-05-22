"""
Port of src/utils/plugins/headlessPluginInstall.ts

Plugin installation for headless/CCR mode.
"""
from __future__ import annotations

from typing import Any, Dict

from ..debug import logForDebugging
from ..log import logError
from .marketplaceManager import (
    clearMarketplacesCache,
    getDeclaredMarketplaces,
    registerSeedMarketplaces,
)
from .pluginBlocklist import detectAndUninstallDelistedPlugins
from .pluginLoader import clearPluginCache
from .reconciler import reconcileMarketplaces
from .zipCache import (
    getZipCacheMarketplacesDir,
    getZipCachePluginsDir,
    isMarketplaceSourceSupportedByZipCache,
    isPluginZipCacheEnabled,
)
from .zipCacheAdapters import syncMarketplacesToZipCache


async def installPluginsForHeadless() -> bool:
    """Install plugins for headless/CCR mode."""
    zip_cache_mode = isPluginZipCacheEnabled()
    logForDebugging(f"installPluginsForHeadless: starting{' (zip cache mode)' if zip_cache_mode else ''}")

    seed_changed = await registerSeedMarketplaces()
    if seed_changed:
        clearMarketplacesCache()
        clearPluginCache("headlessPluginInstall: seed marketplaces registered")

    if zip_cache_mode:
        import os
        os.makedirs(getZipCacheMarketplacesDir(), exist_ok=True)
        os.makedirs(getZipCachePluginsDir(), exist_ok=True)

    declared = getDeclaredMarketplaces()
    declared_count = len(declared)
    plugins_changed = seed_changed

    try:
        if declared_count > 0:
            reconcile_result = await reconcileMarketplaces(
                skip=(lambda name, source: not isMarketplaceSourceSupportedByZipCache(source)) if zip_cache_mode else None,
            )
            marketplaces_changed = len(reconcile_result.get("installed", [])) + len(reconcile_result.get("updated", []))
            if marketplaces_changed > 0:
                clearMarketplacesCache()
                clearPluginCache("headlessPluginInstall: marketplaces reconciled")
                plugins_changed = True

        if zip_cache_mode:
            await syncMarketplacesToZipCache()

        newly_delisted = await detectAndUninstallDelistedPlugins()
        if newly_delisted:
            plugins_changed = True

        if plugins_changed:
            clearPluginCache("headlessPluginInstall: plugins changed")

        return plugins_changed
    except Exception as e:
        logError(e)
        return False

