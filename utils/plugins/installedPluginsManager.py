"""
Port of src/utils/plugins/installedPluginsManager.ts

Manages plugin installation metadata stored in installed_plugins.json.
"""
from __future__ import annotations

import json
import os
import secrets
import shutil
from typing import Any, Dict, List, Optional, Set

from ..debug import logForDebugging
from ..errors import errorMessage, getErrnoCode, isENOENT
from ..log import logError
from ..slowOperations import json_parse, json_stringify
from .pluginDirectories import getPluginsDirectory
from .schemas import (
    InstalledPlugin,
    InstalledPluginsFileV2,
    PluginInstallationEntry,
    PluginScope,
)

_migration_completed = False
_installed_plugins_cache_v2: Optional[InstalledPluginsFileV2] = None
_in_memory_installed_plugins: Optional[InstalledPluginsFileV2] = None


def getInstalledPluginsFilePath() -> str:
    return os.path.join(getPluginsDirectory(), "installed_plugins.json")


def getInstalledPluginsV2FilePath() -> str:
    return os.path.join(getPluginsDirectory(), "installed_plugins_v2.json")


def clearInstalledPluginsCache() -> None:
    global _installed_plugins_cache_v2, _in_memory_installed_plugins
    _installed_plugins_cache_v2 = None
    _in_memory_installed_plugins = None


def migrateToSinglePluginFile() -> None:
    global _migration_completed
    if _migration_completed:
        return
    _migration_completed = True

    v2_path = getInstalledPluginsV2FilePath()
    primary_path = getInstalledPluginsFilePath()

    if os.path.isfile(v2_path):
        try:
            with open(v2_path, "r") as f:
                v2_data = json.loads(f.read())
            with open(primary_path, "w") as f:
                json.dump({"version": 2, "plugins": v2_data.get("plugins", {})}, f, indent=2)
            os.unlink(v2_path)
        except Exception:
            pass
    elif os.path.isfile(primary_path):
        try:
            with open(primary_path, "r") as f:
                data = json.loads(f.read())
            if data.get("version") == 1:
                v2_plugins: Dict[str, List[Dict[str, Any]]] = {}
                for plugin_id, entry in data.get("plugins", {}).items():
                    if isinstance(entry, dict):
                        v2_plugins[plugin_id] = [{
                            "version": entry.get("version", "unknown"),
                            "installedAt": entry.get("installedAt", ""),
                            "lastUpdated": entry.get("lastUpdated", ""),
                            "installPath": entry.get("installPath", ""),
                            "scope": "user",
                        }]
                with open(primary_path, "w") as f:
                    json.dump({"version": 2, "plugins": v2_plugins}, f, indent=2)
        except Exception:
            pass


def resetMigrationState() -> None:
    global _migration_completed
    _migration_completed = False


def loadInstalledPluginsV2() -> InstalledPluginsFileV2:
    global _installed_plugins_cache_v2
    if _installed_plugins_cache_v2 is not None:
        return _installed_plugins_cache_v2

    migrateToSinglePluginFile()
    path = getInstalledPluginsFilePath()

    try:
        if os.path.isfile(path):
            with open(path, "r") as f:
                data = json.loads(f.read())
            if isinstance(data, dict) and "plugins" in data:
                _installed_plugins_cache_v2 = data
                return data
    except Exception:
        pass

    _installed_plugins_cache_v2 = {"version": 2, "plugins": {}}
    return _installed_plugins_cache_v2


def loadInstalledPluginsFromDisk() -> InstalledPluginsFileV2:
    path = getInstalledPluginsFilePath()
    try:
        if os.path.isfile(path):
            with open(path, "r") as f:
                return json.loads(f.read())
    except Exception:
        pass
    return {"version": 2, "plugins": {}}


def getInMemoryInstalledPlugins() -> InstalledPluginsFileV2:
    global _in_memory_installed_plugins
    if _in_memory_installed_plugins is None:
        _in_memory_installed_plugins = loadInstalledPluginsV2()
    return _in_memory_installed_plugins


def addInstalledPlugin(
    plugin_id: str,
    metadata: InstalledPlugin,
    scope: PluginScope = "user",
    project_path: Optional[str] = None,
) -> None:
    data = loadInstalledPluginsV2()
    if "plugins" not in data:
        data["plugins"] = {}
    if plugin_id not in data["plugins"]:
        data["plugins"][plugin_id] = []

    entry: PluginInstallationEntry = {
        "version": metadata.get("version", "unknown"),
        "installedAt": metadata.get("installedAt", ""),
        "lastUpdated": metadata.get("lastUpdated", ""),
        "installPath": metadata.get("installPath", ""),
        "scope": scope,
    }
    if metadata.get("gitCommitSha"):
        entry["gitCommitSha"] = metadata["gitCommitSha"]
    if project_path:
        entry["projectPath"] = project_path

    data["plugins"][plugin_id].append(entry)
    _save_installed_plugins(data)


def removeInstalledPlugin(plugin_id: str) -> Optional[InstalledPlugin]:
    data = loadInstalledPluginsV2()
    if plugin_id in data.get("plugins", {}):
        removed = data["plugins"].pop(plugin_id)
        _save_installed_plugins(data)
        return removed[0] if removed else None
    return None


def isPluginInstalled(plugin_id: str) -> bool:
    data = getInMemoryInstalledPlugins()
    installations = data.get("plugins", {}).get(plugin_id, [])
    return any(_is_installation_relevant(i) for i in installations)


def isPluginGloballyInstalled(plugin_id: str) -> bool:
    data = getInMemoryInstalledPlugins()
    installations = data.get("plugins", {}).get(plugin_id, [])
    return any(i.get("scope") in ("user", "managed") for i in installations)


def _is_installation_relevant(inst: PluginInstallationEntry) -> bool:
    scope = inst.get("scope", "")
    if scope in ("user", "managed"):
        return True
    if scope in ("project", "local"):
        try:
            from ...bootstrap.state import getOriginalCwd
            cwd = getOriginalCwd()
            return inst.get("projectPath") == cwd
        except Exception:
            return True
    return False


def isInstallationRelevantToCurrentProject(inst: PluginInstallationEntry) -> bool:
    return _is_installation_relevant(inst)


def _save_installed_plugins(data: InstalledPluginsFileV2) -> None:
    global _installed_plugins_cache_v2
    path = getInstalledPluginsFilePath()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp_path = f"{path}.{secrets.token_hex(8)}.tmp"
    try:
        with open(tmp_path, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, path)
        _installed_plugins_cache_v2 = data
    except Exception as e:
        logError(e)
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


def hasPendingUpdates() -> bool:
    return False


def getPendingUpdateCount() -> int:
    return 0


def getPendingUpdatesDetails() -> List[Dict[str, Any]]:
    return []


def resetInMemoryState() -> None:
    global _in_memory_installed_plugins
    _in_memory_installed_plugins = None


async def initializeVersionedPlugins() -> None:
    migrateToSinglePluginFile()
    getInMemoryInstalledPlugins()


def removeAllPluginsForMarketplace(marketplace_name: str) -> Dict[str, Any]:
    data = loadInstalledPluginsV2()
    suffix = f"@{marketplace_name}"
    orphaned_paths: List[str] = []
    removed_ids: List[str] = []

    for plugin_id in list(data.get("plugins", {}).keys()):
        if plugin_id.endswith(suffix):
            for entry in data["plugins"][plugin_id]:
                orphaned_paths.append(entry.get("installPath", ""))
            removed_ids.append(plugin_id)
            del data["plugins"][plugin_id]

    if removed_ids:
        _save_installed_plugins(data)
    return {"orphanedPaths": orphaned_paths, "removedPluginIds": removed_ids}


def deletePluginCache(install_path: str) -> None:
    try:
        if os.path.isdir(install_path):
            shutil.rmtree(install_path, ignore_errors=True)
    except Exception as e:
        logForDebugging(f"Failed to delete plugin cache: {install_path}: {e}")


async def getGitCommitSha(dir_path: str) -> Optional[str]:
    try:
        from ..git.gitFilesystem import getHeadForDir
        return await getHeadForDir(dir_path)
    except Exception:
        return None


async def migrateFromEnabledPlugins() -> None:
    pass

