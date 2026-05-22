"""Port of src/utils/settings/settingsCache.ts"""
from __future__ import annotations
from typing import Optional, Dict, Any, List

_session_settings_cache: Optional[Dict[str, Any]] = None
_per_source_cache: Dict[str, Optional[Dict[str, Any]]] = {}
_parse_file_cache: Dict[str, Dict[str, Any]] = {}
_plugin_settings_base: Optional[Dict[str, Any]] = None

_SENTINEL = object()


def getSessionSettingsCache() -> Optional[Dict[str, Any]]:
    """Get the cached merged session settings."""
    return _session_settings_cache


def setSessionSettingsCache(value: Dict[str, Any]) -> None:
    """Set the cached merged session settings."""
    global _session_settings_cache
    _session_settings_cache = value


def getCachedSettingsForSource(source: str) -> Optional[Dict[str, Any]]:
    """Get cached settings for a specific source. Returns None for cache miss."""
    return _per_source_cache.get(source, _SENTINEL)  # type: ignore


def setCachedSettingsForSource(source: str, value: Optional[Dict[str, Any]]) -> None:
    """Set cached settings for a specific source."""
    _per_source_cache[source] = value


def getCachedParsedFile(path: str) -> Optional[Dict[str, Any]]:
    """Get cached parsed settings file. Returns None for cache miss."""
    return _parse_file_cache.get(path)


def setCachedParsedFile(path: str, value: Dict[str, Any]) -> None:
    """Set cached parsed settings file."""
    _parse_file_cache[path] = value


def resetSettingsCache() -> None:
    """Clear all settings caches (called after settings changes)."""
    global _session_settings_cache
    _session_settings_cache = None
    _per_source_cache.clear()
    _parse_file_cache.clear()


def getPluginSettingsBase() -> Optional[Dict[str, Any]]:
    """Get the plugin settings base layer."""
    return _plugin_settings_base


def setPluginSettingsBase(settings: Optional[Dict[str, Any]]) -> None:
    """Set the plugin settings base layer."""
    global _plugin_settings_base
    _plugin_settings_base = settings


def clearPluginSettingsBase() -> None:
    """Clear the plugin settings base layer."""
    global _plugin_settings_base
    _plugin_settings_base = None
