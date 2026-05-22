"""
Port of src/utils/plugins/pluginStartupCheck.ts

Plugin startup checks and installation.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from ..cwd import getCwd
from ..debug import logForDebugging
from ..log import logError
from ..settings.settings import (
    getInitialSettings,
    getSettingsForSource,
    updateSettingsForSource,
)
from .addDirPluginSettings import getAddDirEnabledPlugins
from .installedPluginsManager import getInMemoryInstalledPlugins, migrateFromEnabledPlugins
from .marketplaceManager import getPluginById
from .pluginIdentifier import (
    SETTING_SOURCE_TO_SCOPE,
    ExtendedPluginScope,
    PersistablePluginScope,
    scopeToSettingSource,
)
from .pluginInstallationHelpers import cacheAndRegisterPlugin, registerPluginInstallation
from .schemas import PluginScope, isLocalPluginSource

PluginInstallResult = Dict[str, Any]


async def checkEnabledPlugins() -> List[str]:
    """Checks for enabled plugins across all settings sources."""
    settings = getInitialSettings()
    enabled_plugins: List[str] = []

    add_dir_plugins = getAddDirEnabledPlugins()
    for plugin_id, value in add_dir_plugins.items():
        if "@" in plugin_id and value:
            enabled_plugins.append(plugin_id)

    if settings.get("enabledPlugins"):
        for plugin_id, value in settings["enabledPlugins"].items():
            if "@" not in plugin_id:
                continue
            if plugin_id in enabled_plugins:
                idx = enabled_plugins.index(plugin_id)
                if value:
                    continue
                else:
                    enabled_plugins.pop(idx)
            elif value:
                enabled_plugins.append(plugin_id)

    return enabled_plugins


def getPluginEditableScopes() -> Dict[str, ExtendedPluginScope]:
    """Gets the user-editable scope that owns each enabled plugin."""
    result: Dict[str, ExtendedPluginScope] = {}

    add_dir_plugins = getAddDirEnabledPlugins()
    for plugin_id, value in add_dir_plugins.items():
        if "@" not in plugin_id:
            continue
        if value is True:
            result[plugin_id] = "flag"
        elif value is False:
            result.pop(plugin_id, None)

    scope_sources = [
        ("managed", "policySettings"),
        ("user", "userSettings"),
        ("project", "projectSettings"),
        ("local", "localSettings"),
        ("flag", "flagSettings"),
    ]

    for scope, source in scope_sources:
        settings = getSettingsForSource(source)
        if not settings or "enabledPlugins" not in settings:
            continue
        for plugin_id, value in settings["enabledPlugins"].items():
            if "@" not in plugin_id:
                continue
            if value is True:
                result[plugin_id] = scope
            elif value is False:
                result.pop(plugin_id, None)

    return result


def isPersistableScope(scope: ExtendedPluginScope) -> bool:
    return scope != "flag"


def settingSourceToScope(source: str) -> ExtendedPluginScope:
    return SETTING_SOURCE_TO_SCOPE.get(source, "user")


async def getInstalledPlugins() -> List[str]:
    import asyncio
    asyncio.ensure_future(migrateFromEnabledPlugins())
    v2_data = getInMemoryInstalledPlugins()
    return list(v2_data.get("plugins", {}).keys())


async def findMissingPlugins(enabled_plugins: List[str]) -> List[str]:
    try:
        installed = await getInstalledPlugins()
        not_installed = [pid for pid in enabled_plugins if pid not in installed]
        missing: List[str] = []
        for plugin_id in not_installed:
            try:
                plugin = await getPluginById(plugin_id)
                if plugin:
                    missing.append(plugin_id)
            except Exception:
                pass
        return missing
    except Exception as e:
        logError(e)
        return []


async def installSelectedPlugins(
    plugins_to_install: List[str],
    on_progress: Optional[Any] = None,
    scope: str = "user",
) -> PluginInstallResult:
    project_path = getCwd() if scope != "user" else None
    setting_source = scopeToSettingSource(scope)
    settings = getSettingsForSource(setting_source) or {}
    updated_enabled = dict(settings.get("enabledPlugins", {}))
    installed: List[str] = []
    failed: List[Dict[str, str]] = []

    for i, plugin_id in enumerate(plugins_to_install):
        if not plugin_id:
            continue
        if on_progress:
            on_progress(plugin_id, i + 1, len(plugins_to_install))

        try:
            plugin_info = await getPluginById(plugin_id)
            if not plugin_info:
                failed.append({"name": plugin_id, "error": "Plugin not found in any marketplace"})
                continue

            entry = plugin_info.get("entry", {})
            marketplace_location = plugin_info.get("marketplaceInstallLocation", "")

            if not isLocalPluginSource(entry.get("source")):
                await cacheAndRegisterPlugin(plugin_id, entry, scope, project_path)
            else:
                registerPluginInstallation(
                    {"pluginId": plugin_id, "installPath": os.path.join(marketplace_location, entry.get("source", "")), "version": entry.get("version")},
                    scope, project_path,
                )

            updated_enabled[plugin_id] = True
            installed.append(plugin_id)
        except Exception as e:
            failed.append({"name": plugin_id, "error": str(e)})

    updateSettingsForSource(setting_source, {**settings, "enabledPlugins": updated_enabled})
    return {"installed": installed, "failed": failed}

