"""
Port of src/utils/plugins/addDirPluginSettings.ts

Reads plugin-related settings (enabledPlugins, extraKnownMarketplaces)
from --add-dir directories.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict


SETTINGS_FILES = ("settings.json", "settings.local.json")


def _get_add_dirs():
    try:
        from ...bootstrap.state import getAdditionalDirectoriesForvivianMd
        return getAdditionalDirectoriesForvivianMd()
    except Exception:
        return []


def _parse_settings_file(path: str) -> Dict[str, Any]:
    try:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.loads(f.read())
    except Exception:
        pass
    return {}


def getAddDirEnabledPlugins() -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for dir_path in _get_add_dirs():
        for file_name in SETTINGS_FILES:
            settings = _parse_settings_file(os.path.join(dir_path, ".vivian", file_name))
            if settings and "enabledPlugins" in settings:
                result.update(settings["enabledPlugins"])
    return result


def getAddDirExtraMarketplaces() -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for dir_path in _get_add_dirs():
        for file_name in SETTINGS_FILES:
            settings = _parse_settings_file(os.path.join(dir_path, ".vivian", file_name))
            if settings and "extraKnownMarketplaces" in settings:
                result.update(settings["extraKnownMarketplaces"])
    return result

