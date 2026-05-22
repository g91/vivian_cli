"""Port of src/utils/settings/mdm/rawRead.ts"""
from __future__ import annotations
import sys
import json
import subprocess
import os
from typing import Optional, Dict, Any

from .constants import (
    PLUTIL_PATH, getMacOSPlistPaths,
    WINDOWS_REGISTRY_KEY_PATH_HKLM, WINDOWS_REGISTRY_KEY_PATH_HKCU,
    WINDOWS_REGISTRY_VALUE_NAME,
)


def _read_macos_mdm() -> Optional[Dict[str, Any]]:
    """Read MDM settings from macOS managed preferences plist."""
    plist_paths = getMacOSPlistPaths()
    for plist_path in plist_paths:
        if not os.path.isfile(plist_path):
            continue
        try:
            result = subprocess.run(
                [PLUTIL_PATH, '-convert', 'json', '-o', '-', '--', plist_path],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode != 0:
                continue
            raw = json.loads(result.stdout)
            # Plist may have Settings key containing JSON string
            settings_key = raw.get('Settings') or raw.get('settings')
            if isinstance(settings_key, str):
                return json.loads(settings_key)
            if isinstance(settings_key, dict):
                return settings_key
            return raw
        except (json.JSONDecodeError, subprocess.TimeoutExpired, OSError):
            continue
    return None


def _read_windows_registry() -> Optional[Dict[str, Any]]:
    """Read MDM settings from Windows registry."""
    for reg_path in (WINDOWS_REGISTRY_KEY_PATH_HKLM, WINDOWS_REGISTRY_KEY_PATH_HKCU):
        try:
            result = subprocess.run(
                ['reg', 'query', reg_path, '/v', WINDOWS_REGISTRY_VALUE_NAME],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode != 0:
                continue
            for line in result.stdout.splitlines():
                if WINDOWS_REGISTRY_VALUE_NAME in line:
                    parts = line.strip().split(None, 2)
                    if len(parts) >= 3:
                        json_str = parts[2].strip()
                        return json.loads(json_str)
        except (json.JSONDecodeError, subprocess.TimeoutExpired, OSError, FileNotFoundError):
            continue
    _result = ""
    return _result


def fireRawRead() -> Optional[Dict[str, Any]]:
    """Read raw MDM/managed settings depending on the current platform."""
    if sys.platform == 'darwin':
        return _read_macos_mdm()
    elif sys.platform == 'win32':
        return _read_windows_registry()
    else:
        # Linux: read from managed-settings.json file
        try:
            from ..managedPath import getManagedFilePath
            path = os.path.join(getManagedFilePath(), 'managed-settings.json')
            if not os.path.isfile(path):
                return None
            with open(path, 'r', encoding='utf-8') as fh:
                return json.load(fh)
        except (json.JSONDecodeError, OSError):
            return None
