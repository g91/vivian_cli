"""
Port of src/utils/plugins/pluginLoader.ts

Plugin Loader Module - discovers, loads, and validates vivian Code plugins.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from functools import lru_cache
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from ..debug import logForDebugging
from ..errors import errorMessage, isENOENT
from ..log import logError
from .pluginDirectories import getPluginSeedDirs, getPluginsDirectory
from .pluginIdentifier import parsePluginIdentifier
from .schemas import (
    PluginInstallationEntry,
    PluginManifest,
    PluginMarketplaceEntry,
    PluginScope,
)


def getPluginCachePath() -> str:
    """Get the path where plugin cache is stored."""
    return os.path.join(getPluginsDirectory(), "cache")


def getVersionedCachePathIn(base_dir: str, plugin_id: str, version: str) -> str:
    """Compute the versioned cache path under a specific base plugins directory."""
    parsed = parsePluginIdentifier(plugin_id)
    marketplace = parsed.get("marketplace", "unknown")
    name = parsed["name"]
    return os.path.join(base_dir, "cache", marketplace, name, version)


def getVersionedCachePath(plugin_id: str, version: str) -> str:
    """Get versioned cache path for a plugin under the primary plugins directory."""
    return getVersionedCachePathIn(getPluginsDirectory(), plugin_id, version)


def getVersionedZipCachePath(plugin_id: str, version: str) -> str:
    """Get versioned ZIP cache path for a plugin."""
    from .zipCache import getZipCachePluginsDir
    parsed = parsePluginIdentifier(plugin_id)
    marketplace = parsed.get("marketplace", "unknown")
    name = parsed["name"]
    return os.path.join(getZipCachePluginsDir(), marketplace, name, f"{version}.zip")


def getLegacyCachePath(plugin_name: str) -> str:
    """Get legacy (non-versioned) cache path for a plugin."""
    return os.path.join(getPluginsDirectory(), "cache", plugin_name)


async def resolvePluginPath(plugin_id: str, version: Optional[str] = None) -> str:
    """Resolve plugin path with fallback to legacy location."""
    if version:
        versioned = getVersionedCachePath(plugin_id, version)
        if os.path.isdir(versioned):
            return versioned
    legacy = getLegacyCachePath(parsePluginIdentifier(plugin_id)["name"])
    if os.path.isdir(legacy):
        return legacy
    if version:
        return getVersionedCachePath(plugin_id, version)
    return getLegacyCachePath(parsePluginIdentifier(plugin_id)["name"])


async def copyDir(src: str, dest: str) -> None:
    """Recursively copy a directory."""
    if os.path.isdir(dest):
        shutil.rmtree(dest)
    shutil.copytree(src, dest, symlinks=True, dirs_exist_ok=True)


async def copyPluginToVersionedCache(
    source_path: str,
    plugin_id: str,
    version: str,
    entry: Optional[PluginMarketplaceEntry] = None,
    marketplace_dir: Optional[str] = None,
) -> str:
    """Copy plugin files to versioned cache directory."""
    dest = getVersionedCachePath(plugin_id, version)
    os.makedirs(os.path.dirname(dest), exist_ok=True)

    if entry and marketplace_dir and isinstance(entry.get("source"), str):
        actual_source = os.path.join(marketplace_dir, entry["source"])
        if os.path.isdir(actual_source):
            source_path = actual_source

    if os.path.isdir(dest):
        shutil.rmtree(dest)
    shutil.copytree(source_path, dest, symlinks=True, dirs_exist_ok=True)
    return dest


async def loadPluginManifest(
    manifest_path: str,
    plugin_name: str,
    source: str,
) -> PluginManifest:
    """Loads and validates a plugin manifest from a JSON file."""
    if not os.path.isfile(manifest_path):
        return {
            "name": plugin_name,
            "version": "0.0.0",
            "description": f"Plugin from {source}",
        }

    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.loads(f.read())
        if not isinstance(data, dict):
            raise ValueError("Manifest must be a JSON object")
        return data
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in manifest {manifest_path}: {e}")
    except Exception as e:
        raise ValueError(f"Failed to load manifest {manifest_path}: {e}")


async def createPluginFromPath(
    plugin_path: str,
    source: str,
    enabled: bool,
    fallback_name: str,
    strict: bool = True,
) -> Tuple[Any, List[Dict[str, Any]]]:
    """Create a LoadedPlugin from a directory path."""
    errors: List[Dict[str, Any]] = []
    manifest_path = os.path.join(plugin_path, "plugin.json")

    try:
        manifest = await loadPluginManifest(manifest_path, fallback_name, source)
    except Exception as e:
        manifest = {"name": fallback_name, "version": "0.0.0"}
        errors.append({"type": "manifest-load-failed", "source": source, "error": str(e)})

    name = manifest.get("name", fallback_name)

    commands_path = os.path.join(plugin_path, "commands")
    agents_path = os.path.join(plugin_path, "agents")
    skills_path = os.path.join(plugin_path, "skills")
    output_styles_path = os.path.join(plugin_path, "output-styles")
    hooks_path = os.path.join(plugin_path, "hooks", "hooks.json")

    plugin = type("LoadedPlugin", (), {
        "path": plugin_path,
        "source": source,
        "name": name,
        "enabled": enabled,
        "manifest": manifest,
        "commandsPath": commands_path if os.path.isdir(commands_path) else None,
        "agentsPath": agents_path if os.path.isdir(agents_path) else None,
        "skillsPath": skills_path if os.path.isdir(skills_path) else None,
        "outputStylesPath": output_styles_path if os.path.isdir(output_styles_path) else None,
        "hooksConfig": None,
        "mcpServers": None,
        "lspServers": None,
        "commandsPaths": manifest.get("commands"),
        "agentsPaths": manifest.get("agents"),
        "skillsPaths": manifest.get("skills"),
        "outputStylesPaths": manifest.get("outputStyles"),
        "commandsMetadata": manifest.get("commandsMetadata"),
        "repository": source,
    })()

    return plugin, errors


@lru_cache(maxsize=1)
def _load_all_plugins_cached() -> Tuple[List[Any], List[Any], List[Dict[str, Any]]]:
    """Cached plugin loading."""
    enabled: List[Any] = []
    disabled: List[Any] = []
    errors: List[Dict[str, Any]] = []

    plugins_dir = getPluginsDirectory()
    cache_dir = getPluginCachePath()

    if os.path.isdir(cache_dir):
        for marketplace in os.listdir(cache_dir):
            marketplace_path = os.path.join(cache_dir, marketplace)
            if not os.path.isdir(marketplace_path):
                continue
            for plugin_name in os.listdir(marketplace_path):
                plugin_path = os.path.join(marketplace_path, plugin_name)
                if not os.path.isdir(plugin_path):
                    continue
                for version in os.listdir(plugin_path):
                    version_path = os.path.join(plugin_path, version)
                    if not os.path.isdir(version_path):
                        continue
                    source = f"{plugin_name}@{marketplace}"
                    try:
                        plugin, errs = _create_plugin_sync(version_path, source, True, plugin_name)
                        enabled.append(plugin)
                        errors.extend(errs)
                    except Exception as e:
                        errors.append({"type": "plugin-load-failed", "source": source, "error": str(e)})
                    break

    return enabled, disabled, errors


def _create_plugin_sync(path: str, source: str, enabled: bool, name: str) -> Tuple[Any, List[Dict[str, Any]]]:
    """Synchronous plugin creation for cached loader."""
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(createPluginFromPath(path, source, enabled, name))
    finally:
        loop.close()


async def loadAllPlugins() -> Dict[str, Any]:
    """Main plugin loading function that discovers and loads all plugins."""
    enabled, disabled, errors = _load_all_plugins_cached()
    return {"enabled": enabled, "disabled": disabled, "errors": errors}


async def loadAllPluginsCacheOnly() -> Dict[str, Any]:
    """Cache-only variant of loadAllPlugins."""
    return await loadAllPlugins()


def clearPluginCache(reason: str = "") -> None:
    """Clear the plugin cache."""
    _load_all_plugins_cached.cache_clear()
    if reason:
        logForDebugging(f"Plugin cache cleared: {reason}")


def mergePluginSources(sources: Dict[str, List[Any]]) -> Dict[str, Any]:
    """Merge plugin sources with precedence."""
    all_plugins: List[Any] = []
    all_errors: List[Dict[str, Any]] = []

    for key in ["session", "marketplace", "builtin"]:
        for plugin in sources.get(key, []):
            all_plugins.append(plugin)

    return {"plugins": all_plugins, "errors": all_errors}


_cached_plugin_settings: Dict[str, Any] = {}


def mergePluginSettings(plugins: List[Any]) -> Dict[str, Any]:
    """Merge settings from all enabled plugins into a single record."""
    merged: Dict[str, Any] = {}
    for plugin in plugins:
        if not getattr(plugin, "enabled", True):
            continue
        settings = getattr(plugin, "manifest", {}).get("settings")
        if isinstance(settings, dict):
            merged.update(settings)
    return merged


def cachePluginSettings(plugins: List[Any]) -> None:
    """Cache plugin settings for the session."""
    global _cached_plugin_settings
    _cached_plugin_settings = mergePluginSettings(plugins)

