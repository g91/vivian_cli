"""Port of src/utils/plugins/performStartupChecks.tsx."""
from __future__ import annotations

from typing import Any, Dict
import asyncio

from ..debug import logForDebugging
from .headlessPluginInstall import installPluginsForHeadless
from .marketplaceManager import clearMarketplacesCache, registerSeedMarketplaces
from .pluginLoader import clearPluginCache


SetAppState = Any


def _mark_plugins_need_refresh(setAppState: SetAppState) -> None:
    if not callable(setAppState):
        return

    def _updater(prev_state: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(prev_state, dict):
            return prev_state
        plugins = dict(prev_state.get("plugins", {}))
        if plugins.get("needsRefresh"):
            return prev_state
        plugins["needsRefresh"] = True
        return {**prev_state, "plugins": plugins}

    try:
        setAppState(_updater)
    except Exception:
        pass


async def performStartupChecks(setAppState):
    """Perform plugin startup checks and initiate background installations

This function starts background installation of marketplaces and plugins
from trusted sources (repository and user settings) without blocking startup.
Installation progress and errors are tracked in AppState and shown via notifications.

SECURITY: This function is only called from REPL.tsx after the "trust this folder"
dialog has been confirmed. The trust dialog in cli.tsx blocks all execution until
the user explicitly trusts the current working directory, ensuring that plugin
installations only happen with user consent. This prevents malicious repositories
from automatically installing plugins without user approval.

@param setAppState Function to update app state with installation progress"""
    logForDebugging("performStartupChecks called")

    try:
        seed_changed = await registerSeedMarketplaces()
        if seed_changed:
            clearMarketplacesCache()
            clearPluginCache("performStartupChecks: seed marketplaces changed")
            _mark_plugins_need_refresh(setAppState)

        async def _run_background_installations() -> None:
            try:
                changed = await installPluginsForHeadless()
                if changed:
                    _mark_plugins_need_refresh(setAppState)
            except Exception as error:
                logForDebugging(f"Error initiating background plugin installations: {error}")

        asyncio.create_task(_run_background_installations())
    except Exception as error:
        logForDebugging(f"Error initiating background plugin installations: {error}")

