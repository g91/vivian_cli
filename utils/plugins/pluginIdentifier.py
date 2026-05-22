"""Port of src/utils/plugins/pluginIdentifier.ts."""
from __future__ import annotations

from typing import Any


ExtendedPluginScope = str
PersistablePluginScope = str
ParsedPluginIdentifier = dict[str, Any]

ALLOWED_OFFICIAL_MARKETPLACE_NAMES = {
    "vivian-code-marketplace",
    "vivian-code-plugins",
    "vivian-plugins-official",
    "anthropic-marketplace",
    "anthropic-plugins",
    "agent-skills",
    "life-sciences",
    "knowledge-work-plugins",
}

# Map from SettingSource to plugin scope.
SETTING_SOURCE_TO_SCOPE = {
    "policySettings": "managed",
    "userSettings": "user",
    "projectSettings": "project",
    "localSettings": "local",
    "flagSettings": "flag",
}

_SCOPE_TO_EDITABLE_SOURCE = {
    "user": "userSettings",
    "project": "projectSettings",
    "local": "localSettings",
}


def parsePluginIdentifier(plugin):
    """Parse a plugin identifier string into name and marketplace components."""
    plugin = str(plugin or "")
    if "@" in plugin:
        parts = plugin.split("@")
        return {"name": parts[0] or "", "marketplace": parts[1] if len(parts) > 1 else None}
    return {"name": plugin}


def buildPluginId(name, marketplace=None):
    """Build a plugin ID from name and marketplace."""
    return f"{name}@{marketplace}" if marketplace else str(name)


def isOfficialMarketplaceName(marketplace):
    """Check if a marketplace name is an official (Anthropic-controlled) marketplace."""
    return marketplace is not None and str(marketplace).lower() in ALLOWED_OFFICIAL_MARKETPLACE_NAMES


def scopeToSettingSource(scope):
    """Convert a plugin scope to its corresponding editable setting source."""
    if scope == "managed":
        raise ValueError("Cannot install plugins to managed scope")
    return _SCOPE_TO_EDITABLE_SOURCE[scope]


def settingSourceToScope(source):
    """Convert an editable setting source to its corresponding plugin scope."""
    return SETTING_SOURCE_TO_SCOPE[source]


parse_plugin_identifier = parsePluginIdentifier
build_plugin_id = buildPluginId
is_official_marketplace_name = isOfficialMarketplaceName
scope_to_setting_source = scopeToSettingSource
setting_source_to_scope = settingSourceToScope

