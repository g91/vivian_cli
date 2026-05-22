"""
Port of src/utils/plugins/lspRecommendation.ts

LSP Plugin Recommendation Utility.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Set

from ..binaryCheck import isBinaryInstalled
from ..config import getGlobalConfig, saveGlobalConfig
from ..debug import logForDebugging
from .installedPluginsManager import isPluginInstalled
from .marketplaceManager import getMarketplace, loadKnownMarketplacesConfig
from .schemas import ALLOWED_OFFICIAL_MARKETPLACE_NAMES

LspPluginRecommendation = Dict[str, Any]
MAX_IGNORED_COUNT = 5


def _is_official_marketplace(name: str) -> bool:
    return name.lower() in ALLOWED_OFFICIAL_MARKETPLACE_NAMES


def _extract_lsp_info_from_manifest(lsp_servers: Any) -> Optional[Dict[str, Any]]:
    if not lsp_servers:
        return None
    if isinstance(lsp_servers, str):
        return None
    if isinstance(lsp_servers, list):
        for item in lsp_servers:
            if isinstance(item, dict):
                info = _extract_from_server_config(item)
                if info:
                    return info
        return None
    if isinstance(lsp_servers, dict):
        return _extract_from_server_config(lsp_servers)
    return None


def _extract_from_server_config(config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    extensions: Set[str] = set()
    command: Optional[str] = None
    for server_name, server_config in config.items():
        if not isinstance(server_config, dict):
            continue
        if not command and isinstance(server_config.get("command"), str):
            command = server_config["command"]
        ext_mapping = server_config.get("extensionToLanguage")
        if isinstance(ext_mapping, dict):
            for ext in ext_mapping:
                extensions.add(ext.lower())
    if not command or not extensions:
        return None
    return {"extensions": extensions, "command": command}


async def _get_lsp_plugins_from_marketplaces() -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}
    try:
        config = await loadKnownMarketplacesConfig()
        for marketplace_name in config:
            try:
                marketplace = await getMarketplace(marketplace_name)
                is_official = _is_official_marketplace(marketplace_name)
                for entry in marketplace.get("plugins", []):
                    if not entry.get("lspServers"):
                        continue
                    lsp_info = _extract_lsp_info_from_manifest(entry["lspServers"])
                    if not lsp_info:
                        continue
                    plugin_id = f"{entry['name']}@{marketplace_name}"
                    result[plugin_id] = {
                        "entry": entry, "marketplaceName": marketplace_name,
                        "extensions": lsp_info["extensions"], "command": lsp_info["command"],
                        "isOfficial": is_official,
                    }
            except Exception:
                pass
    except Exception:
        pass
    return result


async def getMatchingLspPlugins(file_path: str) -> List[LspPluginRecommendation]:
    if isLspRecommendationsDisabled():
        return []

    ext = os.path.splitext(file_path)[1].lower()
    if not ext:
        return []

    all_lsp_plugins = await _get_lsp_plugins_from_marketplaces()
    config = getGlobalConfig()
    never_plugins = config.get("lspRecommendationNeverPlugins", [])

    matching: List[Dict[str, Any]] = []
    for plugin_id, info in all_lsp_plugins.items():
        if ext not in info["extensions"]:
            continue
        if plugin_id in never_plugins:
            continue
        if isPluginInstalled(plugin_id):
            continue
        matching.append({"info": info, "pluginId": plugin_id})

    with_binary: List[Dict[str, Any]] = []
    for item in matching:
        if await isBinaryInstalled(item["info"]["command"]):
            with_binary.append(item)

    with_binary.sort(key=lambda x: (0 if x["info"]["isOfficial"] else 1))

    return [{
        "pluginId": item["pluginId"],
        "pluginName": item["info"]["entry"]["name"],
        "marketplaceName": item["info"]["marketplaceName"],
        "description": item["info"]["entry"].get("description"),
        "isOfficial": item["info"]["isOfficial"],
        "extensions": list(item["info"]["extensions"]),
        "command": item["info"]["command"],
    } for item in with_binary]


def addToNeverSuggest(plugin_id: str) -> None:
    def _update(c: Dict[str, Any]) -> Dict[str, Any]:
        current = c.get("lspRecommendationNeverPlugins", [])
        if plugin_id in current:
            return c
        return {**c, "lspRecommendationNeverPlugins": [*current, plugin_id]}
    saveGlobalConfig(_update)


def incrementIgnoredCount() -> None:
    def _update(c: Dict[str, Any]) -> Dict[str, Any]:
        return {**c, "lspRecommendationIgnoredCount": c.get("lspRecommendationIgnoredCount", 0) + 1}
    saveGlobalConfig(_update)


def isLspRecommendationsDisabled() -> bool:
    config = getGlobalConfig()
    return config.get("lspRecommendationDisabled") is True or config.get("lspRecommendationIgnoredCount", 0) >= MAX_IGNORED_COUNT


def resetIgnoredCount() -> None:
    def _update(c: Dict[str, Any]) -> Dict[str, Any]:
        if c.get("lspRecommendationIgnoredCount", 0) == 0:
            return c
        return {**c, "lspRecommendationIgnoredCount": 0}
    saveGlobalConfig(_update)

