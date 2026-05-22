"""
Port of src/utils/plugins/pluginOptionsStorage.ts

Plugin option storage and substitution.
"""
from __future__ import annotations

import os
import re
from functools import lru_cache
from typing import Any, Dict, Optional

from ..debug import logForDebugging
from ..log import logError
from ..secureStorage import getSecureStorage
from ..settings.settings import getSettings_DEPRECATED, getSettingsForSource, updateSettingsForSource
from ..slowOperations import json_parse, json_stringify
from .mcpbHandler import UserConfigValues, UserConfigSchema, validateUserConfig
from .pluginDirectories import getPluginDataDir

PluginOptionValues = Dict[str, Any]
PluginOptionSchema = Dict[str, Any]


def getPluginStorageId(plugin: Any) -> str:
    """Canonical storage key for a plugin's options."""
    return getattr(plugin, "source", str(plugin))


@lru_cache(maxsize=128)
def _load_plugin_options_cached(plugin_id: str) -> PluginOptionValues:
    settings = getSettings_DEPRECATED()
    non_sensitive = settings.get("pluginConfigs", {}).get(plugin_id, {}).get("options", {})

    storage = getSecureStorage()
    sensitive = storage.read().get("pluginSecrets", {}).get(plugin_id, {}) if storage else {}

    return {**non_sensitive, **sensitive}


def loadPluginOptions(plugin_id: str) -> PluginOptionValues:
    return _load_plugin_options_cached(plugin_id)


def clearPluginOptionsCache() -> None:
    _load_plugin_options_cached.cache_clear()


def savePluginOptions(plugin_id: str, values: PluginOptionValues, schema: PluginOptionSchema) -> None:
    non_sensitive: Dict[str, Any] = {}
    sensitive: Dict[str, str] = {}

    for key, value in values.items():
        if schema.get(key, {}).get("sensitive") is True:
            sensitive[key] = str(value)
        else:
            non_sensitive[key] = value

    sensitive_keys = set(sensitive.keys())
    non_sensitive_keys = set(non_sensitive.keys())

    # Write sensitive to secureStorage first
    storage = getSecureStorage()
    if storage:
        existing = storage.read() or {}
        existing_secrets = existing.get("pluginSecrets", {})
        existing_plugin = existing_secrets.get(plugin_id, {})

        # Scrub non-sensitive keys from secureStorage
        scrubbed = {k: v for k, v in existing_plugin.items() if k not in non_sensitive_keys}
        scrubbed.update(sensitive)

        if scrubbed or sensitive:
            if "pluginSecrets" not in existing:
                existing["pluginSecrets"] = {}
            existing["pluginSecrets"][plugin_id] = scrubbed
            result = storage.update(existing)
            if not result.get("success"):
                logError(Exception(f"Failed to save plugin secrets for {plugin_id}: {result.get('error')}"))

    # Write non-sensitive to settings
    settings = getSettings_DEPRECATED()
    if "pluginConfigs" not in settings:
        settings["pluginConfigs"] = {}
    if plugin_id not in settings["pluginConfigs"]:
        settings["pluginConfigs"][plugin_id] = {}
    if "options" not in settings["pluginConfigs"][plugin_id]:
        settings["pluginConfigs"][plugin_id]["options"] = {}

    existing_options = settings["pluginConfigs"][plugin_id]["options"]
    # Scrub sensitive keys from settings
    for k in sensitive_keys:
        existing_options.pop(k, None)
    existing_options.update(non_sensitive)

    updateSettingsForSource("userSettings", settings)
    clearPluginOptionsCache()


def deletePluginOptions(plugin_id: str) -> None:
    # Remove from settings
    settings = getSettings_DEPRECATED()
    if settings.get("pluginConfigs", {}).get(plugin_id):
        del settings["pluginConfigs"][plugin_id]
        updateSettingsForSource("userSettings", settings)

    # Remove from secureStorage
    storage = getSecureStorage()
    if storage:
        existing = storage.read() or {}
        secrets = existing.get("pluginSecrets", {})
        if plugin_id in secrets:
            del secrets[plugin_id]
            # Also remove per-server composite keys
            prefix = f"{plugin_id}/"
            to_remove = [k for k in secrets if k.startswith(prefix)]
            for k in to_remove:
                del secrets[k]
            existing["pluginSecrets"] = secrets
            storage.update(existing)

    clearPluginOptionsCache()


def getUnconfiguredOptions(plugin: Any) -> PluginOptionSchema:
    manifest_schema = getattr(plugin, "manifest", {}).get("userConfig", {})
    if not manifest_schema:
        return {}

    plugin_id = getPluginStorageId(plugin)
    saved = loadPluginOptions(plugin_id)
    validation = validateUserConfig(saved, manifest_schema)
    if validation.get("valid"):
        return {}

    unconfigured: PluginOptionSchema = {}
    for key, field_schema in manifest_schema.items():
        single = validateUserConfig({key: saved.get(key)}, {key: field_schema})
        if not single.get("valid"):
            unconfigured[key] = field_schema
    return unconfigured


def substitutePluginVariables(value: str, plugin: Optional[Dict[str, Any]] = None) -> str:
    """Substitute ${vivian_PLUGIN_ROOT} and ${vivian_PLUGIN_DATA}."""
    if not plugin:
        return value

    path = plugin.get("path", "")
    source = plugin.get("source")

    def _normalize(p: str) -> str:
        return p.replace("\\", "/") if os.name == "nt" else p

    result = value.replace("${vivian_PLUGIN_ROOT}", _normalize(path))
    if source:
        result = result.replace("${vivian_PLUGIN_DATA}", _normalize(getPluginDataDir(source)))
    return result


def substituteUserConfigVariables(value: str, user_config: PluginOptionValues) -> str:
    """Substitute ${user_config.KEY} with saved option values. Throws on missing keys."""
    def _replacer(match: re.Match) -> str:
        key = match.group(1)
        if key not in user_config:
            raise KeyError(f"Missing user_config key: {key}")
        return str(user_config[key])
    return re.sub(r"\$\{user_config\.([^}]+)\}", _replacer, value)


def substituteUserConfigInContent(content: str, options: PluginOptionValues, schema: PluginOptionSchema) -> str:
    """Content-safe variant for skill/agent prose."""
    def _replacer(match: re.Match) -> str:
        key = match.group(1)
        if key not in options:
            return match.group(0)  # Leave literal
        if schema.get(key, {}).get("sensitive") is True:
            return f"[sensitive:{key}]"
        return str(options[key])
    return re.sub(r"\$\{user_config\.([^}]+)\}", _replacer, content)

