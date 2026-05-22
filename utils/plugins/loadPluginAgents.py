"""
Port of src/utils/plugins/loadPluginAgents.ts

Loads plugin agent definitions from plugin directories.
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Any, Dict, List, Optional, Set

from ..debug import logForDebugging
from ..frontmatterParser import parseFrontmatter
from ..fsOperations import getFsImplementation, isDuplicatePath
from .pluginLoader import loadAllPluginsCacheOnly
from .pluginOptionsStorage import substitutePluginVariables
from .walkPluginMarkdown import walkPluginMarkdown


async def _load_agents_from_directory(
    agents_path: str,
    plugin_name: str,
    source_name: str,
    plugin_path: str,
    plugin_manifest: Dict[str, Any],
    loaded_paths: Set[str],
) -> List[Dict[str, Any]]:
    agents: List[Dict[str, Any]] = []

    async def _on_file(full_path: str, namespace: List[str]) -> None:
        fs = getFsImplementation()
        if isDuplicatePath(fs, full_path, loaded_paths):
            return
        try:
            content = await fs.readFile(full_path, encoding="utf-8")
            frontmatter, markdown_content = parseFrontmatter(content, full_path)

            base_name = frontmatter.get("name") or os.path.basename(full_path).replace(".md", "")
            name_parts = [plugin_name, *namespace, base_name]
            agent_type = ":".join(name_parts)

            when_to_use = frontmatter.get("description") or frontmatter.get("when-to-use") or f"Agent from {plugin_name} plugin"
            system_prompt = substitutePluginVariables(markdown_content.strip(), {"path": plugin_path, "source": source_name})

            agents.append({
                "agentType": agent_type,
                "whenToUse": str(when_to_use),
                "getSystemPrompt": lambda sp=system_prompt: sp,
                "source": "plugin",
                "plugin": source_name,
                "filename": base_name,
            })
        except Exception as e:
            logForDebugging(f"Failed to load agent from {full_path}: {e}", level="error")

    await walkPluginMarkdown(agents_path, _on_file, log_label="agents")
    return agents


@lru_cache(maxsize=1)
def _get_plugin_agents_cached() -> List[Dict[str, Any]]:
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_load_plugin_agents())
    finally:
        loop.close()


async def _load_plugin_agents() -> List[Dict[str, Any]]:
    result = await loadAllPluginsCacheOnly()
    enabled = result.get("enabled", [])
    all_agents: List[Dict[str, Any]] = []

    for plugin in enabled:
        loaded_paths: Set[str] = set()
        if getattr(plugin, "agentsPath", None):
            agents = await _load_agents_from_directory(
                plugin.agentsPath, plugin.name, plugin.source,
                plugin.path, plugin.manifest, loaded_paths,
            )
            all_agents.extend(agents)

    return all_agents


async def loadPluginAgents() -> List[Dict[str, Any]]:
    return _get_plugin_agents_cached()


def clearPluginAgentCache() -> None:
    _get_plugin_agents_cached.cache_clear()

