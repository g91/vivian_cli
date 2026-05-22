"""PluginSettings — mirrors src/commands/plugin/PluginSettings.tsx."""
from __future__ import annotations

def plugin_settings(plugin_name: str) -> dict:
    return {"name": plugin_name, "settings": {}}
