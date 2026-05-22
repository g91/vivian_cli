"""Port of src/utils/settings/pluginOnlyPolicy.ts"""
from __future__ import annotations
from typing import Optional

PLUGIN_ONLY_SOURCES = {'plugin', 'policySettings', 'built-in', 'command'}
ADMIN_TRUSTED_SOURCES = {'policySettings'}


def isRestrictedToPluginOnly() -> bool:
    """Return True if only plugin-provided settings are trusted in this session."""
    try:
        from .settings import getSettingsForSource
        policy = getSettingsForSource('policySettings')
        return bool(policy and policy.get('restrictToPlugin'))
    except Exception:
        return False


def isSourceAdminTrusted(source: str) -> bool:
    """Return True if the settings source is trusted as an admin-managed source."""
    return source in ADMIN_TRUSTED_SOURCES


def isSourcePluginTrusted(source: str) -> bool:
    """Return True if the source is trusted in plugin-only mode."""
    return source in PLUGIN_ONLY_SOURCES


def shouldApplySettingsFromSource(source: str) -> bool:
    """Return True if settings from the given source should be applied."""
    if isRestrictedToPluginOnly():
        return isSourcePluginTrusted(source)
    if source is None: return False
    return True
