"""
Port of src/utils/plugins/cacheUtils.ts

Cache management utilities for plugins.
"""
from __future__ import annotations

import os
import shutil
import time
from typing import Optional, Set

from ..debug import logForDebugging
from ..errors import getErrnoCode
from ..log import logError

ORPHANED_AT_FILENAME = ".orphaned_at"
CLEANUP_AGE_MS = 7 * 24 * 60 * 60 * 1000


def clearAllPluginCaches() -> None:
    try:
        from .pluginLoader import clearPluginCache
        clearPluginCache()
    except Exception:
        pass
    try:
        from .loadPluginCommands import clearPluginCommandCache
        clearPluginCommandCache()
    except Exception:
        pass
    try:
        from .loadPluginAgents import clearPluginAgentCache
        clearPluginAgentCache()
    except Exception:
        pass
    try:
        from .loadPluginHooks import clearPluginHookCache, pruneRemovedPluginHooks
        clearPluginHookCache()
        import asyncio
        try:
            asyncio.ensure_future(pruneRemovedPluginHooks())
        except Exception:
            pass
    except Exception:
        pass
    try:
        from .pluginOptionsStorage import clearPluginOptionsCache
        clearPluginOptionsCache()
    except Exception:
        pass
    try:
        from .loadPluginOutputStyles import clearPluginOutputStyleCache
        clearPluginOutputStyleCache()
    except Exception:
        pass


def clearAllCaches() -> None:
    clearAllPluginCaches()
    try:
        from ...commands import clearCommandsCache
        clearCommandsCache()
    except Exception:
        pass
    try:
        from ...tools.AgentTool.loadAgentsDir import clearAgentDefinitionsCache
        clearAgentDefinitionsCache()
    except Exception:
        pass
    try:
        from ...tools.SkillTool.prompt import clearPromptCache
        clearPromptCache()
    except Exception:
        pass
    try:
        from ..attachments import resetSentSkillNames
        resetSentSkillNames()
    except Exception:
        pass


async def markPluginVersionOrphaned(version_path: str) -> None:
    try:
        orphaned_path = os.path.join(version_path, ORPHANED_AT_FILENAME)
        with open(orphaned_path, "w") as f:
            f.write(str(int(time.time() * 1000)))
    except Exception as e:
        logForDebugging(f"Failed to write .orphaned_at: {version_path}: {e}")


async def cleanupOrphanedPluginVersionsInBackground() -> None:
    try:
        from .zipCache import isPluginZipCacheEnabled
        if isPluginZipCacheEnabled():
            return
    except Exception:
        pass

    try:
        from .installedPluginsManager import loadInstalledPluginsFromDisk
        from .pluginLoader import getPluginCachePath

        installed_data = loadInstalledPluginsFromDisk()
        installed_paths: Set[str] = set()
        for installations in installed_data.get("plugins", {}).values():
            for entry in installations:
                installed_paths.add(entry.get("installPath", ""))

        cache_path = getPluginCachePath()
        now_ms = int(time.time() * 1000)

        if not os.path.isdir(cache_path):
            return

        for marketplace in os.listdir(cache_path):
            marketplace_path = os.path.join(cache_path, marketplace)
            if not os.path.isdir(marketplace_path):
                continue
            for plugin in os.listdir(marketplace_path):
                plugin_path = os.path.join(marketplace_path, plugin)
                if not os.path.isdir(plugin_path):
                    continue
                for version in os.listdir(plugin_path):
                    version_path = os.path.join(plugin_path, version)
                    if not os.path.isdir(version_path):
                        continue
                    if version_path in installed_paths:
                        _remove_orphaned_at_marker(version_path)
                        continue
                    _process_orphaned_version(version_path, now_ms)
    except Exception as e:
        logForDebugging(f"Plugin cache cleanup failed: {e}")


def _remove_orphaned_at_marker(version_path: str) -> None:
    orphaned_path = os.path.join(version_path, ORPHANED_AT_FILENAME)
    try:
        os.unlink(orphaned_path)
    except FileNotFoundError:
        pass
    except Exception as e:
        logForDebugging(f"Failed to remove .orphaned_at: {version_path}: {e}")


def _process_orphaned_version(version_path: str, now_ms: int) -> None:
    orphaned_path = os.path.join(version_path, ORPHANED_AT_FILENAME)
    try:
        mtime_ms = int(os.stat(orphaned_path).st_mtime * 1000)
    except FileNotFoundError:
        import asyncio
        asyncio.ensure_future(markPluginVersionOrphaned(version_path))
        return
    except Exception as e:
        logForDebugging(f"Failed to stat orphaned marker: {version_path}: {e}")
        return

    if now_ms - mtime_ms > CLEANUP_AGE_MS:
        try:
            shutil.rmtree(version_path, ignore_errors=True)
        except Exception as e:
            logForDebugging(f"Failed to delete orphaned version: {version_path}: {e}")

