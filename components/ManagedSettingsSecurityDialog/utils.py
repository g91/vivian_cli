"""Managed settings security helpers.

Mirrors src/components/ManagedSettingsSecurityDialog/utils.ts.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional

from ...utils.managedEnvConstants import DANGEROUS_SHELL_SETTINGS, SAFE_ENV_VARS
from ...utils.settings.types import SettingsJson
from ...utils.slowOperations import jsonStringify


@dataclass(slots=True)
class DangerousSettings:
    shellSettings: Dict[str, str]
    envVars: Dict[str, str]
    hasHooks: bool
    hooks: Any = None


def extractDangerousSettings(
    settings: Optional[Mapping[str, Any] | SettingsJson],
) -> DangerousSettings:
    if not settings:
        return DangerousSettings(shellSettings={}, envVars={}, hasHooks=False)

    shell_settings: Dict[str, str] = {}
    for key in DANGEROUS_SHELL_SETTINGS:
        value = settings.get(key)
        if isinstance(value, str) and value:
            shell_settings[key] = value

    env_vars: Dict[str, str] = {}
    env = settings.get("env")
    if isinstance(env, Mapping):
        for key, value in env.items():
            if isinstance(value, str) and value and key.upper() not in SAFE_ENV_VARS:
                env_vars[str(key)] = value

    hooks = settings.get("hooks")
    has_hooks = isinstance(hooks, Mapping) and bool(hooks)

    return DangerousSettings(
        shellSettings=shell_settings,
        envVars=env_vars,
        hasHooks=has_hooks,
        hooks=hooks if has_hooks else None,
    )


def hasDangerousSettings(dangerous: DangerousSettings) -> bool:
    return bool(dangerous.shellSettings or dangerous.envVars or dangerous.hasHooks)


def hasDangerousSettingsChanged(
    oldSettings: Optional[Mapping[str, Any] | SettingsJson],
    newSettings: Optional[Mapping[str, Any] | SettingsJson],
) -> bool:
    old_dangerous = extractDangerousSettings(oldSettings)
    new_dangerous = extractDangerousSettings(newSettings)

    if not hasDangerousSettings(new_dangerous):
        return False
    if not hasDangerousSettings(old_dangerous):
        return True

    old_json = jsonStringify(
        {
            "shellSettings": old_dangerous.shellSettings,
            "envVars": old_dangerous.envVars,
            "hooks": old_dangerous.hooks,
        }
    )
    new_json = jsonStringify(
        {
            "shellSettings": new_dangerous.shellSettings,
            "envVars": new_dangerous.envVars,
            "hooks": new_dangerous.hooks,
        }
    )
    return old_json != new_json


def formatDangerousSettingsList(dangerous: DangerousSettings) -> list[str]:
    items: list[str] = []
    items.extend(dangerous.shellSettings.keys())
    items.extend(dangerous.envVars.keys())
    if dangerous.hasHooks:
        items.append("hooks")
    return items


extract_dangerous_settings = extractDangerousSettings
has_dangerous_settings = hasDangerousSettings
has_dangerous_settings_changed = hasDangerousSettingsChanged
format_dangerous_settings_list = formatDangerousSettingsList