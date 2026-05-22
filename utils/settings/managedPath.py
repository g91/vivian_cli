"""Port of src/utils/settings/managedPath.ts"""
from __future__ import annotations
import os
import sys
from functools import lru_cache


@lru_cache(maxsize=1)
def getManagedFilePath() -> str:
    """Get the path to the managed settings directory based on the current platform."""
    # Allow override for testing
    if os.environ.get('USER_TYPE') == 'ant' and os.environ.get('vivian_CODE_MANAGED_SETTINGS_PATH'):
        return os.environ['vivian_CODE_MANAGED_SETTINGS_PATH']
    if sys.platform == 'darwin':
        return '/Library/Application Support/vivianCode'
    elif sys.platform == 'win32':
        return 'C:\\Program Files\\vivianCode'
    else:
        return '/etc/vivian-code'


@lru_cache(maxsize=1)
def getManagedSettingsDropInDir() -> str:
    """Get the path to the managed-settings.d/ drop-in directory."""
    return os.path.join(getManagedFilePath(), 'managed-settings.d')
