"""
Port of src/utils/plugins/loadPluginOutputStyles.ts

Loads plugin output styles from plugin directories.
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Any, Dict, List, Set

from ..debug import logForDebugging
from ..frontmatterParser import parseFrontmatter
from ..fsOperations import getFsImplementation, isDuplicatePath
from ..markdownConfigLoader import extractDescriptionFromMarkdown
from .pluginLoader import loadAllPluginsCacheOnly
from .walkPluginMarkdown import walkPluginMarkdown


async def _load_output_styles_from_directory(
    output_styles_path: str,
    plugin_name: str,
    loaded_paths: Set[str],
) -> List[Dict[str, Any]]:
    styles: List[Dict[str, Any]] = []

    async def _on_file(full_path: str, namespace: List[str]) -> None:
        fs = getFsImplementation()
        if isDuplicatePath(fs, full_path, loaded_paths):
            return
        try:
            content = await fs.readFile(full_path, encoding="utf-8")
            frontmatter, markdown_content = parseFrontmatter(content, full_path)

            base_name = frontmatter.get("name") or os.path.basename(full_path).replace(".md", "")
            name = f"{plugin_name}:{base_name}"
            description = frontmatter.get("description") or extractDescriptionFromMarkdown(
                markdown_content, f"Output style from {plugin_name} plugin"
            )

            styles.append({
                "name": name,
                "description": str(description),
                "prompt": markdown_content.strip(),
                "source": "plugin",
            })
        except Exception as e:
            logForDebugging(f"Failed to load output style from {full_path}: {e}", level="error")

    await walkPluginMarkdown(output_styles_path, _on_file, log_label="output-styles")
    return styles


@lru_cache(maxsize=1)
def _get_plugin_output_styles_cached() -> List[Dict[str, Any]]:
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_load_plugin_output_styles())
    finally:
        loop.close()


async def _load_plugin_output_styles() -> List[Dict[str, Any]]:
    result = await loadAllPluginsCacheOnly()
    enabled = result.get("enabled", [])
    all_styles: List[Dict[str, Any]] = []

    for plugin in enabled:
        loaded_paths: Set[str] = set()
        if getattr(plugin, "outputStylesPath", None):
            styles = await _load_output_styles_from_directory(
                plugin.outputStylesPath, plugin.name, loaded_paths,
            )
            all_styles.extend(styles)

    return all_styles


async def loadPluginOutputStyles() -> List[Dict[str, Any]]:
    return _get_plugin_output_styles_cached()


def clearPluginOutputStyleCache() -> None:
    _get_plugin_output_styles_cached.cache_clear()

