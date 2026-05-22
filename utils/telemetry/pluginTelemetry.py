"""Port of src/utils/telemetry/pluginTelemetry.ts."""
from __future__ import annotations

import hashlib
import os
import re
from typing import Any

from ...services.analytics.index import logEvent
from ..plugins.pluginIdentifier import isOfficialMarketplaceName, parsePluginIdentifier


TelemetryPluginScope = str
EnabledVia = str
InvocationTrigger = str
SkillExecutionContext = str
InstallSource = str
PluginCommandErrorCategory = str

BUILTIN_MARKETPLACE_NAME = "builtin"
PLUGIN_ID_HASH_SALT = "vivian-plugin-telemetry-v1"


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _managed_has(managedNames: Any, name: str) -> bool:
    if managedNames is None:
        return False
    try:
        return name in managedNames
    except TypeError:
        return False


def hashPluginId(name, marketplace=None):
    """Opaque per-plugin aggregation key."""
    key = f"{name}@{str(marketplace).lower()}" if marketplace else str(name)
    return hashlib.sha256((key + PLUGIN_ID_HASH_SALT).encode("utf-8")).hexdigest()[:16]


def getTelemetryPluginScope(name, marketplace, managedNames):
    if marketplace == BUILTIN_MARKETPLACE_NAME:
        return "default-bundle"
    if isOfficialMarketplaceName(marketplace):
        return "official"
    if _managed_has(managedNames, name):
        return "org"
    return "user-local"


def getEnabledVia(plugin, managedNames, seedDirs):
    if _get(plugin, "isBuiltin", False):
        return "default-enable"
    if _managed_has(managedNames, _get(plugin, "name", "")):
        return "org-policy"

    plugin_path = str(_get(plugin, "path", "") or "")
    for seed_dir in seedDirs or []:
        seed_dir = str(seed_dir)
        prefix = seed_dir if seed_dir.endswith(os.sep) else seed_dir + os.sep
        if plugin_path.startswith(prefix):
            return "seed-mount"
    return "user-install"


def buildPluginTelemetryFields(name, marketplace, managedNames=None):
    """Common plugin telemetry fields keyed off name@marketplace."""
    scope = getTelemetryPluginScope(name, marketplace, managedNames)
    is_anthropic_controlled = scope in ("official", "default-bundle")
    return {
        "plugin_id_hash": hashPluginId(name, marketplace),
        "plugin_scope": scope,
        "plugin_name_redacted": name if is_anthropic_controlled else "third-party",
        "marketplace_name_redacted": marketplace if (is_anthropic_controlled and marketplace) else "third-party",
        "is_official_plugin": is_anthropic_controlled,
    }


def buildPluginCommandTelemetryFields(pluginInfo, managedNames=None):
    """Build plugin telemetry fields from plugin invocation info."""
    repository = _get(pluginInfo, "repository", "")
    manifest = _get(pluginInfo, "pluginManifest", {})
    parsed = parsePluginIdentifier(repository)
    plugin_name = _get(manifest, "name", "")
    return buildPluginTelemetryFields(plugin_name, parsed.get("marketplace"), managedNames)


def logPluginsEnabledForSession(plugins, managedNames, seedDirs):
    """Emit tengu_plugin_enabled_for_session once per enabled plugin at session start."""
    for plugin in plugins or []:
        parsed = parsePluginIdentifier(_get(plugin, "repository", ""))
        marketplace = parsed.get("marketplace")
        manifest = _get(plugin, "manifest", {})
        skills_paths = _get(plugin, "skillsPaths", None) or []
        commands_paths = _get(plugin, "commandsPaths", None) or []
        logEvent(
            "tengu_plugin_enabled_for_session",
            {
                "_PROTO_plugin_name": _get(plugin, "name", ""),
                **({"_PROTO_marketplace_name": marketplace} if marketplace else {}),
                **buildPluginTelemetryFields(_get(plugin, "name", ""), marketplace, managedNames),
                "enabled_via": getEnabledVia(plugin, managedNames, seedDirs),
                "skill_path_count": (1 if _get(plugin, "skillsPath", None) else 0) + len(skills_paths),
                "command_path_count": (1 if _get(plugin, "commandsPath", None) else 0) + len(commands_paths),
                "has_mcp": _get(manifest, "mcpServers", None) is not None,
                "has_hooks": _get(plugin, "hooksConfig", None) is not None,
                **({"version": _get(manifest, "version")} if _get(manifest, "version", None) else {}),
            },
        )


def classifyPluginCommandError(error):
    msg = str(_get(error, "message", error))
    if re.search(r"ENOTFOUND|ECONNREFUSED|EAI_AGAIN|ETIMEDOUT|ECONNRESET|network|Could not resolve|Connection refused|timed out", msg, re.I):
        return "network"
    if re.search(r"\b404\b|not found|does not exist|no such plugin", msg, re.I):
        return "not-found"
    if re.search(r"\b40[13]\b|EACCES|EPERM|permission denied|unauthorized", msg, re.I):
        return "permission"
    if re.search(r"invalid|malformed|schema|validation|parse error", msg, re.I):
        return "validation"
    return "unknown"


def logPluginLoadErrors(errors, managedNames):
    """Emit tengu_plugin_load_failed once per startup plugin error."""
    for err in errors or []:
        parsed = parsePluginIdentifier(_get(err, "source", ""))
        plugin_name = _get(err, "plugin", None) or parsed.get("name", "")
        marketplace = parsed.get("marketplace")
        logEvent(
            "tengu_plugin_load_failed",
            {
                "error_category": _get(err, "type", "unknown"),
                "_PROTO_plugin_name": plugin_name,
                **({"_PROTO_marketplace_name": marketplace} if marketplace else {}),
                **buildPluginTelemetryFields(plugin_name, marketplace, managedNames),
            },
        )


hash_plugin_id = hashPluginId
get_telemetry_plugin_scope = getTelemetryPluginScope
get_enabled_via = getEnabledVia
build_plugin_telemetry_fields = buildPluginTelemetryFields
build_plugin_command_telemetry_fields = buildPluginCommandTelemetryFields
log_plugins_enabled_for_session = logPluginsEnabledForSession
classify_plugin_command_error = classifyPluginCommandError
log_plugin_load_errors = logPluginLoadErrors

