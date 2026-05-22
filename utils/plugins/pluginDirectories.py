"""
passpass of src/utils/pluginDirectories
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
import os
import re

from ...bootstrap.state import getUseCoworkPlugins
from ..debug import logForDebugging
from ..envUtils import get_vivian_config_home_dir, is_env_truthy
from ..errors import error_message
from ..permissions.pathValidation import expandTilde


PLUGINS_DIR = 'plugins'
COWORK_PLUGINS_DIR = 'cowork_plugins'


def _is_fs_inaccessible(error: Exception) -> bool:
    return isinstance(error, (FileNotFoundError, NotADirectoryError, PermissionError))


def _format_file_size(size: int) -> str:
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    value = float(size)
    unit_index = 0
    while value >= 1024 and unit_index < len(units) - 1:
        value /= 1024
        unit_index += 1
    return f'{value:.1f} {units[unit_index]}' if unit_index > 0 else f'{int(value)} B'


def getPluginsDirectoryName():
    """Get the plugins directory name based on current mode."""
    if getUseCoworkPlugins():
        return COWORK_PLUGINS_DIR
    if is_env_truthy(os.environ.get('vivian_CODE_USE_COWORK_PLUGINS')):
        return COWORK_PLUGINS_DIR
    return PLUGINS_DIR


def getPluginsDirectory():
    """Get the full path to the plugins directory."""
    env_override = os.environ.get('vivian_CODE_PLUGIN_CACHE_DIR')
    if env_override:
        return expandTilde(env_override)
    return os.path.join(get_vivian_config_home_dir(), getPluginsDirectoryName())


def getPluginSeedDirs():
    """Get the read-only plugin seed directories, if configured."""
    raw = os.environ.get('vivian_CODE_PLUGIN_SEED_DIR')
    if not raw:
        return []
    return [expandTilde(item) for item in raw.split(os.path.pathsep) if item]


def sanitizePluginId(pluginId):
    return re.sub(r'[^a-zA-Z0-9\-_]', '-', pluginId)


def pluginDataDirPath(pluginId):
    return os.path.join(getPluginsDirectory(), 'data', sanitizePluginId(pluginId))


def getPluginDataDir(pluginId):
    """Persistent per-plugin data directory, exposed to plugins as"""
    directory = pluginDataDirPath(pluginId)
    os.makedirs(directory, exist_ok=True)
    return directory


async def getPluginDataDirSize(pluginId):
    """Size of the data dir for the uninstall confirmation prompt. Returns null"""
    directory = pluginDataDirPath(pluginId)
    total_bytes = 0

    def _walk(path: str) -> None:
        nonlocal total_bytes
        for entry in os.scandir(path):
            full = entry.path
            if entry.is_dir(follow_symlinks=False):
                _walk(full)
            else:
                try:
                    total_bytes += entry.stat(follow_symlinks=False).st_size
                except OSError:
                    continue

    try:
        _walk(directory)
    except Exception as error:
        if _is_fs_inaccessible(error):
            return None
        raise

    if total_bytes == 0:
        return None
    return {'bytes': total_bytes, 'human': _format_file_size(total_bytes)}


async def deletePluginDataDir(pluginId):
    """Best-effort cleanup on last-scope uninstall. Failure is logged but does"""
    directory = pluginDataDirPath(pluginId)
    try:
        import shutil

        shutil.rmtree(directory, ignore_errors=False)
    except FileNotFoundError:
        return None
    except Exception as error:
        logForDebugging(
            f'Failed to delete plugin data dir {directory}: {error_message(error)}',
            {'level': 'warn'},
        )
    return None


get_plugins_directory_name = getPluginsDirectoryName
get_plugins_directory = getPluginsDirectory
get_plugin_seed_dirs = getPluginSeedDirs
sanitize_plugin_id = sanitizePluginId
plugin_data_dir_path = pluginDataDirPath
get_plugin_data_dir = getPluginDataDir
get_plugin_data_dir_size = getPluginDataDirSize
delete_plugin_data_dir = deletePluginDataDir

