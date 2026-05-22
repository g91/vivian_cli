"""
Port of src/utils/plugins/managedPlugins.ts

Plugin names locked by org policy (policySettings.enabledPlugins).
"""
from __future__ import annotations

from typing import Optional, Set


def getManagedPluginNames() -> Optional[Set[str]]:
    """Get plugin names locked by org policy.
    
    Returns None when managed settings declare no plugin entries.
    """
    try:
        from ..settings.settings import getSettingsForSource
        enabled_plugins = getSettingsForSource("policySettings")
        if not enabled_plugins or "enabledPlugins" not in enabled_plugins:
            return None
        
        names: Set[str] = set()
        for plugin_id, value in enabled_plugins["enabledPlugins"].items():
            if not isinstance(value, bool) or "@" not in plugin_id:
                continue
            name = plugin_id.split("@")[0]
            if name:
                names.add(name)
        
        return names if names else None
    except Exception:
        return None

