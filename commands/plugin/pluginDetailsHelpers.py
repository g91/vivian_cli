"""pluginDetailsHelpers — mirrors src/commands/plugin/pluginDetailsHelpers.tsx."""
from __future__ import annotations

def format_plugin_details(plugin: dict) -> str:
    return f"{plugin.get('name', 'unknown')} v{plugin.get('version', '?')}: {plugin.get('description', '')}"
