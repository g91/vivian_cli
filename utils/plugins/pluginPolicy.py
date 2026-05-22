"""
Port of src/utils/plugins/pluginPolicy.ts

Plugin policy checks backed by managed settings (policySettings).
"""
from __future__ import annotations

from typing import Optional


def isPluginBlockedByPolicy(plugin_id: str) -> bool:
    """Check if a plugin is force-disabled by org policy.
    
    Policy-blocked plugins cannot be installed or enabled by the user at any
    scope. Used as the single source of truth for policy blocking across the
    install chokepoint, enable op, and UI filters.
    """
    try:
        from ..settings.settings import getSettingsForSource
        policy_enabled = getSettingsForSource("policySettings")
        if policy_enabled and "enabledPlugins" in policy_enabled:
            return policy_enabled["enabledPlugins"].get(plugin_id) is False
    except Exception:
        pass
    return False

