"""Port of src/utils/settings/settings.ts"""
from __future__ import annotations
import json
import os
import sys
from typing import Optional, Dict, Any, List, Tuple

from .settingsCache import (
    _SENTINEL as _SETTINGS_SENTINEL,
    getCachedSettingsForSource, setCachedSettingsForSource,
    getSessionSettingsCache, setSessionSettingsCache, resetSettingsCache,
)
from .validation import validateSettingsJson


def getSettingsFilePathForSource(source: str) -> Optional[str]:
    """Get the file system path for a specific settings source."""
    cwd = os.getcwd()
    home = os.path.expanduser('~')
    mapping = {
        'userSettings': os.path.join(home, '.vivian', 'settings.json'),
        'projectSettings': os.path.join(cwd, '.vivian', 'settings.json'),
        'localSettings': os.path.join(cwd, '.vivian', 'settings.local.json'),
    }
    if source in mapping:
        return mapping[source]
    if source == 'policySettings':
        try:
            from .managedPath import getManagedFilePath
            return os.path.join(getManagedFilePath(), 'managed-settings.json')
        except Exception:
            return None
    return None


def _parse_settings_file(path: str) -> Optional[Dict[str, Any]]:
    """Read and parse a JSON settings file, returning None on error."""
    if not path or not os.path.isfile(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as fh:
            raw = fh.read().strip()
            if not raw:
                return {}
            return json.loads(raw)
    except (json.JSONDecodeError, OSError):
        return None


def getSettingsForSource(source: str) -> Optional[Dict[str, Any]]:
    """Get settings for a specific source, using the cache if available."""
    cached = getCachedSettingsForSource(source)
    if cached is not _SETTINGS_SENTINEL:
        return cached  # type: ignore

    if source == 'flagSettings':
        # Flag settings come from CLI flags, not a file
        result = _flag_settings
    elif source == 'policySettings':
        # policySettings: first source wins (remote > MDM > file)
        result = None
        try:
            from ...services.remoteManagedSettings.syncCacheState import (
                getRemoteManagedSettingsSyncFromCache,
            )

            remote_settings = getRemoteManagedSettingsSyncFromCache()
            if remote_settings and len(remote_settings) > 0:
                result = remote_settings
        except Exception:
            result = None

        # MDM/managed settings
        if result is None:
            try:
                from .mdm.settings import getMdmSettings

                result = getMdmSettings()
            except Exception:
                result = None

        if result is None:
            # Fall back to file-based managed settings
            path = getSettingsFilePathForSource(source)
            result = _parse_settings_file(path)
    else:
        path = getSettingsFilePathForSource(source)
        result = _parse_settings_file(path)

    setCachedSettingsForSource(source, result)
    return result


def updateSettingsForSource(source: str, new_data: Dict[str, Any]) -> None:
    """Write updated settings to a source's settings file."""
    path = getSettingsFilePathForSource(source)
    if path is None:
        raise ValueError(f"Cannot update settings for source: {source}")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        from .internalWrites import markInternalWrite
        markInternalWrite(path)
    except Exception:
        pass
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(new_data, fh, indent=2)
        fh.write('\n')
    setCachedSettingsForSource(source, new_data)
    setSessionSettingsCache(None)  # type: ignore


def loadManagedFileSettings() -> Optional[Dict[str, Any]]:
    """Load the managed-settings.json file from the managed directory."""
    try:
        from .managedPath import getManagedFilePath
        base = getManagedFilePath()
        path = os.path.join(base, 'managed-settings.json')
        return _parse_settings_file(path)
    except Exception:
        return None


def getMergedSettings() -> Dict[str, Any]:
    """Get the fully merged settings for the current session."""
    cached = getSessionSettingsCache()
    if cached is not None:
        return cached

    sources = ['userSettings', 'projectSettings', 'localSettings', 'flagSettings', 'policySettings']
    merged: Dict[str, Any] = {}

    for source in sources:
        data = getSettingsForSource(source)
        if not data:
            continue
        _deep_merge_settings(merged, data)

    setSessionSettingsCache(merged)
    return merged


def _deep_merge_settings(target: Dict[str, Any], source: Dict[str, Any]) -> None:
    """Deep merge source settings into target, merging permissions lists."""
    for key, value in source.items():
        if key == 'permissions' and isinstance(value, dict) and isinstance(target.get('permissions'), dict):
            perms = target['permissions']
            for behavior, rules in value.items():
                if isinstance(rules, list):
                    existing = list(perms.get(behavior, []))
                    for rule in rules:
                        if rule not in existing:
                            existing.append(rule)
                    perms[behavior] = existing
                else:
                    perms[behavior] = rules
        elif isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_merge_settings(target[key], value)
        else:
            target[key] = value


# Module-level flag settings storage
_flag_settings: Optional[Dict[str, Any]] = None


def setFlagSettings(settings: Optional[Dict[str, Any]]) -> None:
    """Set settings that came from CLI flags."""
    global _flag_settings
    _flag_settings = settings
    setCachedSettingsForSource('flagSettings', settings)
    setSessionSettingsCache(None)  # type: ignore


getInitialSettings = getMergedSettings


def getSettings_DEPRECATED() -> Dict[str, Any]:
    return getMergedSettings()
