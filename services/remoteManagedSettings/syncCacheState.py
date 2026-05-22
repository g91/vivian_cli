"""Leaf state for remote managed settings sync cache.

Mirrors src/services/remoteManagedSettings/syncCacheState.ts.
"""
from __future__ import annotations

from os.path import join
from typing import Optional

from ...utils.envUtils import get_vivian_config_home_dir
from ...utils.fileRead import readFileSync
from ...utils.jsonRead import strip_bom
from ...utils.settings.settingsCache import resetSettingsCache
from ...utils.settings.types import SettingsJson
from ...utils.slowOperations import jsonParse


SETTINGS_FILENAME = "remote-settings.json"

_session_cache: Optional[SettingsJson] = None
_eligible: Optional[bool] = None


def setSessionCache(value: Optional[SettingsJson]) -> None:
    global _session_cache
    _session_cache = value


def resetSyncCache() -> None:
    global _session_cache, _eligible
    _session_cache = None
    _eligible = None


def setEligibility(value: bool) -> bool:
    global _eligible
    _eligible = value
    return value


def getSettingsPath() -> str:
    return join(get_vivian_config_home_dir(), SETTINGS_FILENAME)


def _load_settings() -> Optional[SettingsJson]:
    try:
        content = readFileSync(getSettingsPath())
        data = jsonParse(strip_bom(content))
    except Exception:
        return None

    if not isinstance(data, dict):
        return None
    return data


def getRemoteManagedSettingsSyncFromCache() -> Optional[SettingsJson]:
    global _session_cache
    if _eligible is not True:
        return None
    if _session_cache is not None:
        return _session_cache

    cached_settings = _load_settings()
    if cached_settings is None:
        return None

    _session_cache = cached_settings
    resetSettingsCache()
    return cached_settings


set_session_cache = setSessionCache
reset_sync_cache = resetSyncCache
set_eligibility = setEligibility
get_settings_path = getSettingsPath
get_remote_managed_settings_sync_from_cache = getRemoteManagedSettingsSyncFromCache