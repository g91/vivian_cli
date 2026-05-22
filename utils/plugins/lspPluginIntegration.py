"""
Port of src/utils/plugins/lspPluginIntegration.ts

LSP server integration for plugins.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from ..debug import logForDebugging
from ..errors import isENOENT, toError
from ..log import logError
from ..slowOperations import json_parse
from .pluginDirectories import getPluginDataDir
from .pluginOptionsStorage import (
    PluginOptionValues,
    loadPluginOptions,
    substitutePluginVariables,
    substituteUserConfigVariables,
)


def _validate_path_within_plugin(plugin_path: str, relative_path: str) -> Optional[str]:
    resolved_plugin = os.path.realpath(plugin_path)
    resolved_file = os.path.realpath(os.path.join(plugin_path, relative_path))
    rel = os.path.relpath(resolved_file, resolved_plugin)
    if rel.startswith("..") or os.path.isabs(rel):
        return None
    return resolved_file


async def loadPluginLspServers(
    plugin: Any,
    errors: Optional[List[Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    if errors is None:
        errors = []
    servers: Dict[str, Any] = {}

    # Check for .lsp.json
    lsp_json_path = os.path.join(plugin.path, ".lsp.json")
    try:
        if os.path.isfile(lsp_json_path):
            with open(lsp_json_path, "r") as f:
                data = json.loads(f.read())
            if isinstance(data, dict):
                servers.update(data)
    except Exception as e:
        if not isENOENT(e):
            errors.append({"type": "lsp-config-invalid", "plugin": plugin.name, "serverName": ".lsp.json", "error": str(e)})

    # Check manifest.lspServers
    manifest_servers = plugin.manifest.get("lspServers")
    if manifest_servers:
        if isinstance(manifest_servers, dict):
            servers.update(manifest_servers)
        elif isinstance(manifest_servers, str):
            validated = _validate_path_within_plugin(plugin.path, manifest_servers)
            if validated and os.path.isfile(validated):
                try:
                    with open(validated, "r") as f:
                        data = json.loads(f.read())
                    if isinstance(data, dict):
                        servers.update(data)
                except Exception as e:
                    errors.append({"type": "lsp-config-invalid", "plugin": plugin.name, "serverName": manifest_servers, "error": str(e)})

    return servers if servers else None


def resolvePluginLspEnvironment(
    config: Dict[str, Any],
    plugin: Dict[str, Any],
    user_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    resolved = dict(config)

    def _resolve(val: str) -> str:
        val = substitutePluginVariables(val, plugin)
        if user_config:
            val = substituteUserConfigVariables(val, user_config)
        return os.path.expandvars(val)

    if resolved.get("command"):
        resolved["command"] = _resolve(resolved["command"])
    if resolved.get("args"):
        resolved["args"] = [_resolve(a) for a in resolved["args"]]

    resolved_env = {
        "vivian_PLUGIN_ROOT": plugin.get("path", ""),
        "vivian_PLUGIN_DATA": getPluginDataDir(plugin.get("source", "")),
        **(resolved.get("env") or {}),
    }
    for k, v in list(resolved_env.items()):
        if k not in ("vivian_PLUGIN_ROOT", "vivian_PLUGIN_DATA"):
            resolved_env[k] = _resolve(v)
    resolved["env"] = resolved_env

    return resolved


def addPluginScopeToLspServers(
    servers: Dict[str, Any],
    plugin_name: str,
) -> Dict[str, Any]:
    scoped: Dict[str, Any] = {}
    for name, config in servers.items():
        scoped_name = f"plugin:{plugin_name}:{name}"
        scoped[scoped_name] = {**config, "scope": "dynamic", "source": plugin_name}
    return scoped


async def getPluginLspServers(
    plugin: Any,
    errors: Optional[List[Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    if not getattr(plugin, "enabled", True):
        return None
    servers = getattr(plugin, "lspServers", None) or await loadPluginLspServers(plugin, errors)
    if not servers:
        return None
    return addPluginScopeToLspServers(servers, plugin.name)


async def extractLspServersFromPlugins(
    plugins: List[Any],
    errors: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    if errors is None:
        errors = []
    all_servers: Dict[str, Any] = {}
    for plugin in plugins:
        if not getattr(plugin, "enabled", True):
            continue
        servers = await loadPluginLspServers(plugin, errors)
        if servers:
            scoped = addPluginScopeToLspServers(servers, plugin.name)
            all_servers.update(scoped)
            plugin.lspServers = servers
    return all_servers

