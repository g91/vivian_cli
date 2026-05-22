"""
Port of src/utils/plugins/mcpPluginIntegration.ts

MCP server integration for plugins.
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


async def loadPluginMcpServers(
    plugin: Any,
    errors: Optional[List[Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    if errors is None:
        errors = []
    servers: Dict[str, Any] = {}

    # Check for .mcp.json
    mcp_json_path = os.path.join(plugin.path, ".mcp.json")
    try:
        if os.path.isfile(mcp_json_path):
            with open(mcp_json_path, "r") as f:
                data = json.loads(f.read())
            mcp_servers = data.get("mcpServers", data) if isinstance(data, dict) else {}
            if isinstance(mcp_servers, dict):
                servers.update(mcp_servers)
    except Exception as e:
        if not isENOENT(e):
            errors.append({"type": "mcp-config-invalid", "plugin": plugin.name, "error": str(e)})

    # Check manifest.mcpServers
    manifest_servers = plugin.manifest.get("mcpServers")
    if manifest_servers:
        if isinstance(manifest_servers, dict):
            servers.update(manifest_servers)
        elif isinstance(manifest_servers, str):
            path = os.path.join(plugin.path, manifest_servers)
            if os.path.isfile(path):
                try:
                    with open(path, "r") as f:
                        data = json.loads(f.read())
                    mcp = data.get("mcpServers", data) if isinstance(data, dict) else {}
                    if isinstance(mcp, dict):
                        servers.update(mcp)
                except Exception as e:
                    errors.append({"type": "mcp-config-invalid", "plugin": plugin.name, "error": str(e)})

    return servers if servers else None


def resolvePluginMcpEnvironment(
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

    server_type = resolved.get("type", "stdio")
    if server_type in (None, "stdio"):
        if resolved.get("command"):
            resolved["command"] = _resolve(resolved["command"])
        if resolved.get("args"):
            resolved["args"] = [_resolve(a) for a in resolved["args"]]
    elif server_type in ("sse", "http", "ws"):
        if resolved.get("url"):
            resolved["url"] = _resolve(resolved["url"])

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


def addPluginScopeToServers(
    servers: Dict[str, Any],
    plugin_name: str,
    plugin_source: str,
) -> Dict[str, Any]:
    scoped: Dict[str, Any] = {}
    for name, config in servers.items():
        scoped_name = f"plugin:{plugin_name}:{name}"
        scoped[scoped_name] = {**config, "scope": "dynamic", "pluginSource": plugin_source}
    return scoped


async def getPluginMcpServers(
    plugin: Any,
    errors: Optional[List[Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    if not getattr(plugin, "enabled", True):
        return None
    servers = getattr(plugin, "mcpServers", None) or await loadPluginMcpServers(plugin, errors)
    if not servers:
        return None
    return addPluginScopeToServers(servers, plugin.name, plugin.source)


async def extractMcpServersFromPlugins(
    plugins: List[Any],
    errors: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    if errors is None:
        errors = []
    all_servers: Dict[str, Any] = {}
    for plugin in plugins:
        if not getattr(plugin, "enabled", True):
            continue
        servers = await loadPluginMcpServers(plugin, errors)
        if servers:
            scoped = addPluginScopeToServers(servers, plugin.name, plugin.source)
            all_servers.update(scoped)
            plugin.mcpServers = servers
    return all_servers

