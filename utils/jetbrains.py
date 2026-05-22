"""Port of src/utils/jetbrains.ts."""
from __future__ import annotations

from typing import Any, Dict, List
import os
import os.path
import asyncio
import platform


PLUGIN_PREFIX = "vivian-code-jetbrains-plugin"
ideNameToDirMap: Dict[str, List[str]] = {
    "pycharm": ["PyCharm"],
    "intellij": ["IntelliJIdea", "IdeaIC"],
    "webstorm": ["WebStorm"],
    "phpstorm": ["PhpStorm"],
    "rubymine": ["RubyMine"],
    "clion": ["CLion"],
    "goland": ["GoLand"],
    "rider": ["Rider"],
    "datagrip": ["DataGrip"],
    "appcode": ["AppCode"],
    "dataspell": ["DataSpell"],
    "aqua": ["Aqua"],
    "gateway": ["Gateway"],
    "fleet": ["Fleet"],
    "androidstudio": ["AndroidStudio"],
}
pluginInstalledCache: Dict[str, bool] = {}
pluginInstalledPromiseCache: Dict[str, asyncio.Task[bool]] = {}

def buildCommonPluginDirectoryPaths(ideName):
    home_dir = os.path.expanduser("~")
    directories: List[str] = []
    ide_patterns = ideNameToDirMap.get(str(ideName).lower())
    if not ide_patterns:
        return directories

    app_data = os.environ.get("APPDATA") or os.path.join(home_dir, "AppData", "Roaming")
    local_app_data = os.environ.get("LOCALAPPDATA") or os.path.join(home_dir, "AppData", "Local")
    current_platform = platform.system().lower()

    if current_platform == "darwin":
        directories.extend(
            [
                os.path.join(home_dir, "Library", "Application Support", "JetBrains"),
                os.path.join(home_dir, "Library", "Application Support"),
            ]
        )
        if str(ideName).lower() == "androidstudio":
            directories.append(os.path.join(home_dir, "Library", "Application Support", "Google"))
    elif current_platform == "windows":
        directories.extend([os.path.join(app_data, "JetBrains"), os.path.join(local_app_data, "JetBrains"), app_data])
        if str(ideName).lower() == "androidstudio":
            directories.append(os.path.join(local_app_data, "Google"))
    elif current_platform == "linux":
        directories.extend(
            [
                os.path.join(home_dir, ".config", "JetBrains"),
                os.path.join(home_dir, ".local", "share", "JetBrains"),
            ]
        )
        for pattern in ide_patterns:
            directories.append(os.path.join(home_dir, f".{pattern}"))
        if str(ideName).lower() == "androidstudio":
            directories.append(os.path.join(home_dir, ".config", "Google"))
    return directories


async def detectPluginDirectories(ideName):
    found_directories: List[str] = []
    plugin_dir_paths = buildCommonPluginDirectoryPaths(ideName)
    ide_patterns = ideNameToDirMap.get(str(ideName).lower())
    if not ide_patterns:
        return found_directories

    current_platform = platform.system().lower()
    for base_dir in plugin_dir_paths:
        try:
            entries = os.scandir(base_dir)
        except Exception:
            continue

        with entries:
            for entry in entries:
                for pattern in ide_patterns:
                    if not entry.name.startswith(pattern):
                        continue
                    try:
                        if not (entry.is_dir() or entry.is_symlink()):
                            continue
                    except Exception:
                        continue
                    directory = os.path.join(base_dir, entry.name)
                    if current_platform == "linux":
                        found_directories.append(directory)
                    else:
                        plugin_dir = os.path.join(directory, "plugins")
                        if os.path.exists(plugin_dir):
                            found_directories.append(plugin_dir)
                    break

    deduped: List[str] = []
    seen = set()
    for directory in found_directories:
        if directory not in seen:
            seen.add(directory)
            deduped.append(directory)
    return deduped


async def isJetBrainsPluginInstalled(ideType):
    plugin_dirs = await detectPluginDirectories(ideType)
    for directory in plugin_dirs:
        plugin_path = os.path.join(directory, PLUGIN_PREFIX)
        if os.path.exists(plugin_path):
            return True
    return False


async def isJetBrainsPluginInstalledMemoized(ideType, forceRefresh=False):
    if not forceRefresh:
        existing = pluginInstalledPromiseCache.get(ideType)
        if existing:
            return await existing

    task = asyncio.create_task(isJetBrainsPluginInstalled(ideType))
    pluginInstalledPromiseCache[ideType] = task
    result = await task
    pluginInstalledCache[ideType] = result
    return result


async def isJetBrainsPluginInstalledCached(ideType, forceRefresh=False):
    if forceRefresh:
        pluginInstalledCache.pop(ideType, None)
        pluginInstalledPromiseCache.pop(ideType, None)
    return await isJetBrainsPluginInstalledMemoized(ideType, forceRefresh)


def isJetBrainsPluginInstalledCachedSync(ideType):
    """Returns the cached result of isJetBrainsPluginInstalled synchronously."""
    return pluginInstalledCache.get(ideType) or False


build_common_plugin_directory_paths = buildCommonPluginDirectoryPaths
detect_plugin_directories = detectPluginDirectories
is_jetbrains_plugin_installed = isJetBrainsPluginInstalled
is_jetbrains_plugin_installed_memoized = isJetBrainsPluginInstalledMemoized
is_jetbrains_plugin_installed_cached = isJetBrainsPluginInstalledCached
is_jetbrains_plugin_installed_cached_sync = isJetBrainsPluginInstalledCachedSync

