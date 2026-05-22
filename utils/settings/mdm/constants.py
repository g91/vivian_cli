"""Port of src/utils/settings/mdm/constants.ts"""
from __future__ import annotations
import os
import sys

MACOS_PREFERENCE_DOMAIN = 'com.anthropic.viviancode'

WINDOWS_REGISTRY_KEY_PATH_HKLM = 'HKLM\\SOFTWARE\\Policies\\vivianCode'
WINDOWS_REGISTRY_KEY_PATH_HKCU = 'HKCU\\SOFTWARE\\Policies\\vivianCode'
WINDOWS_REGISTRY_VALUE_NAME = 'Settings'

PLUTIL_PATH = '/usr/bin/plutil'


def getMacOSPlistPaths() -> list:
    """Get the ordered list of macOS plist file paths to check for MDM settings."""
    try:
        import pwd
        username = pwd.getpwuid(os.getuid()).pw_name
    except Exception:
        username = os.environ.get('USER', 'nobody')
    return [
        f'/Library/Managed Preferences/{username}/{MACOS_PREFERENCE_DOMAIN}.plist',
        f'/Library/Managed Preferences/{MACOS_PREFERENCE_DOMAIN}.plist',
        f'{os.path.expanduser("~")}/Library/Preferences/{MACOS_PREFERENCE_DOMAIN}.plist',
    ]
