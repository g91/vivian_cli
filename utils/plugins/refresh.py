"""
Port of src/utils/plugins/refresh.ts

Layer-3 refresh primitive: swap active plugin components in the running session.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List

from ...bootstrap.state import getOriginalCwd
from ..debug import logForDebugging
from ..errors import errorMessage
from ..log import logError
from .cacheUtils import clearAllCaches
from .loadPluginCommands import getPluginCommands
from .loadPluginHooks import loadPluginHooks
from .lspPluginIntegration import loadPluginLspServers
from .mcpPluginIntegration import loadPluginMcpServers
from .orphanedPluginFilter import clearPluginCacheExclusions
from .pluginLoader import loadAllPlugins

SetAppState = Callable[[Callable[[Dict[str, Any]], Dict[str, Any]]], None]
RefreshActivePluginsResult = Dict[str, Any]


async def refreshActivePlugins(set_app_state: SetAppState) -> RefreshActivePluginsResult:
    """Refresh all active plugin components."""
    logForDebugging("refreshActivePlugins: clearing all plugin caches")
    clearAllCaches()
    clearPluginCacheExclusions()

    plugin_result = await loadAllPlugins()
    plugin_commands = await getPluginCommands()

    try:
        from ...tools.AgentTool.loadAgentsDir import getAgentDefinitionsWithOverrides
        agent_definitions = await getAgentDefinitionsWithOverrides(getOriginalCwd())
    except Exception:
        agent_definitions = {"allAgents": []}

    enabled = plugin_result.get("enabled", [])
    disabled = plugin_result.get("disabled", [])
    errors = plugin_result.get("errors", [])

    mcp_count = 0
    lsp_count = 0
    for p in enabled:
        if not getattr(p, "mcpServers", None):
            servers = await loadPluginMcpServers(p, errors)
            if servers:
                p.mcpServers = servers
        mcp_count += len(getattr(p, "mcpServers", {}) or {})

        if not getattr(p, "lspServers", None):
            servers = await loadPluginLspServers(p, errors)
            if servers:
                p.lspServers = servers
        lsp_count += len(getattr(p, "lspServers", {}) or {})

    hook_load_failed = False
    try:
        await loadPluginHooks()
    except Exception as e:
        hook_load_failed = True
        logError(e)

    hook_count = 0
    for p in enabled:
        hooks_config = getattr(p, "hooksConfig", None)
        if hooks_config:
            for matchers in hooks_config.values():
                for m in (matchers or []):
                    hook_count += len(m.get("hooks", []))

    return {
        "enabled_count": len(enabled),
        "disabled_count": len(disabled),
        "command_count": len(plugin_commands),
        "agent_count": len(agent_definitions.get("allAgents", [])),
        "hook_count": hook_count,
        "mcp_count": mcp_count,
        "lsp_count": lsp_count,
        "error_count": len(errors) + (1 if hook_load_failed else 0),
        "agentDefinitions": agent_definitions,
        "pluginCommands": plugin_commands,
    }
    return result


def errorKey(e):
    return e.type == f"generic-error:{e.source}:{e.error}" if 'generic-error' else f"{e.type}:{e.source}"