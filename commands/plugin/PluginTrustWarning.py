"""PluginTrustWarning — mirrors src/commands/plugin/PluginTrustWarning.tsx."""
from __future__ import annotations

def show_trust_warning(plugin_name: str) -> str:
    return f"Warning: You are about to install '{plugin_name}'. Review the plugin source before trusting it."
