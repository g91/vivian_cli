"""
passpasspasspass of src/utils/plugins/pluginFlagging.ts
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
import secrets
from typing import Any

from ..debug import logForDebugging
from ..log import logError
from ..slowOperations import json_parse, json_stringify
from .pluginDirectories import getPluginsDirectory


FlaggedPlugin = dict[str, Any]

FLAGGED_PLUGINS_FILENAME = 'flagged-plugins.json'
SEEN_EXPIRY_MS = 48 * 60 * 60 * 1000
cache: dict[str, FlaggedPlugin] | None = None


def getFlaggedPluginsPath():
    return os.path.join(getPluginsDirectory(), FLAGGED_PLUGINS_FILENAME)


def parsePluginsData(content):
    try:
        parsed = json_parse(content)
    except Exception:
        return {}
    if not isinstance(parsed, dict):
        return {}
    plugins = parsed.get('plugins')
    if not isinstance(plugins, dict):
        return {}
    result: dict[str, FlaggedPlugin] = {}
    for plugin_id, entry in plugins.items():
        if not isinstance(entry, dict):
            continue
        flagged_at = entry.get('flaggedAt')
        seen_at = entry.get('seenAt')
        if not isinstance(flagged_at, str):
            continue
        parsed_entry: FlaggedPlugin = {'flaggedAt': flagged_at}
        if isinstance(seen_at, str):
            parsed_entry['seenAt'] = seen_at
        result[str(plugin_id)] = parsed_entry
    return result


async def readFromDisk():
    try:
        with open(getFlaggedPluginsPath(), 'r', encoding='utf-8') as handle:
            return parsePluginsData(handle.read())
    except Exception:
        return {}


async def writeToDisk(plugins):
    global cache
    file_path = getFlaggedPluginsPath()
    temp_path = f"{file_path}.{secrets.token_hex(8)}.tmp"
    try:
        os.makedirs(getPluginsDirectory(), exist_ok=True)
        content = json_stringify({'plugins': plugins}, indent=2)
        with open(temp_path, 'w', encoding='utf-8') as handle:
            handle.write(content)
        os.replace(temp_path, file_path)
        cache = plugins
    except Exception as error:
        logError(error)
        try:
            os.unlink(temp_path)
        except Exception:
            pass
    return None


async def loadFlaggedPlugins():
    """Load flagged plugins from disk into the module cache.
Must be called (and awaited) before getFlaggedPlugins() returns
meaningful data. Called by useManagePlugins during plugin refresh."""
    global cache
    all_plugins = await readFromDisk()
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    changed = False

    for plugin_id, entry in list(all_plugins.items()):
        seen_at = entry.get('seenAt')
        if not isinstance(seen_at, str):
            continue
        try:
            seen_ms = int(datetime.fromisoformat(seen_at.replace('Z', '+00:00')).timestamp() * 1000)
        except ValueError:
            continue
        if now_ms - seen_ms >= SEEN_EXPIRY_MS:
            del all_plugins[plugin_id]
            changed = True

    cache = all_plugins
    if changed:
        await writeToDisk(all_plugins)
    return None


def getFlaggedPlugins():
    """Get all flagged plugins from the in-memory cache.
Returns an empty object if loadFlaggedPlugins() has not been called yet."""
    return cache or {}


async def addFlaggedPlugin(pluginId):
    """Add a plugin to the flagged list.

@param pluginId "name@marketplace" format"""
    global cache
    if cache is None:
        cache = await readFromDisk()
    updated = {
        **cache,
        pluginId: {'flaggedAt': datetime.now(timezone.utc).isoformat()},
    }
    await writeToDisk(updated)
    logForDebugging(f'Flagged plugin: {pluginId}')
    return None


async def markFlaggedPluginsSeen(pluginIds):
    """Mark flagged plugins as seen. Called when the Installed view renders
flagged plugins. Sets seenAt on entries that don't already have it.
After 48 hours from seenAt, entries are auto-cleared on next load."""
    global cache
    if cache is None:
        cache = await readFromDisk()
    now = datetime.now(timezone.utc).isoformat()
    changed = False
    updated = dict(cache)
    for plugin_id in pluginIds:
        entry = updated.get(plugin_id)
        if entry and not entry.get('seenAt'):
            updated[plugin_id] = {**entry, 'seenAt': now}
            changed = True
    if changed:
        await writeToDisk(updated)
    return None


async def removeFlaggedPlugin(pluginId):
    """Remove a plugin from the flagged list. Called when the user dismisses
a flagged plugin notification in /plugins."""
    global cache
    if cache is None:
        cache = await readFromDisk()
    if pluginId not in cache:
        return None
    updated = dict(cache)
    updated.pop(pluginId, None)
    cache = updated
    await writeToDisk(updated)
    return None


get_flagged_plugins_path = getFlaggedPluginsPath
parse_plugins_data = parsePluginsData
read_from_disk = readFromDisk
write_to_disk = writeToDisk
load_flagged_plugins = loadFlaggedPlugins
get_flagged_plugins = getFlaggedPlugins
add_flagged_plugin = addFlaggedPlugin
mark_flagged_plugins_seen = markFlaggedPluginsSeen
remove_flagged_plugin = removeFlaggedPlugin

