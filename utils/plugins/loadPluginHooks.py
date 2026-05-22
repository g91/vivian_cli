"""
Port of src/utils/plugins/loadPluginHooks.ts

Loads and registers plugin hooks.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, List

from ..debug import logForDebugging
from .pluginLoader import loadAllPluginsCacheOnly

HOOK_EVENTS = [
    "PreToolUse", "PostToolUse", "PostToolUseFailure", "Notification",
    "UserPromptSubmit", "SessionStart", "SessionEnd", "Stop", "StopFailure",
    "SubagentStart", "SubagentStop", "PreCompact", "PostCompact",
    "PermissionRequest", "PermissionDenied", "Setup", "TeammateIdle",
    "TaskCreated", "TaskCompleted", "Elicitation", "ElicitationResult",
    "ConfigChange", "WorktreeCreate", "WorktreeRemove",
    "InstructionsLoaded", "CwdChanged", "FileChanged",
]


@lru_cache(maxsize=1)
def _load_plugin_hooks_cached() -> Dict[str, List[Dict[str, Any]]]:
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_load_plugin_hooks())
    finally:
        loop.close()


async def _load_plugin_hooks() -> Dict[str, List[Dict[str, Any]]]:
    result = await loadAllPluginsCacheOnly()
    enabled = result.get("enabled", [])

    all_hooks: Dict[str, List[Dict[str, Any]]] = {event: [] for event in HOOK_EVENTS}

    for plugin in enabled:
        hooks_config = getattr(plugin, "hooksConfig", None)
        if not hooks_config:
            continue
        for event, matchers in hooks_config.items():
            if event in all_hooks:
                for matcher in matchers:
                    all_hooks[event].append({
                        **matcher,
                        "pluginRoot": plugin.path,
                        "pluginName": plugin.name,
                        "pluginId": plugin.source,
                    })

    return all_hooks


async def loadPluginHooks() -> Dict[str, List[Dict[str, Any]]]:
    return _load_plugin_hooks_cached()


def clearPluginHookCache() -> None:
    _load_plugin_hooks_cached.cache_clear()


async def pruneRemovedPluginHooks() -> None:
    return None

