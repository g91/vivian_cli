"""PluginOptionsFlow — mirrors src/commands/plugin/PluginOptionsFlow.tsx."""
from __future__ import annotations

def plugin_options_flow(plugin_name: str) -> dict:
    return {"name": plugin_name, "step": "configure", "options": {}}
