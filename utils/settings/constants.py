"""Port of src/utils/settings/constants.ts"""
from __future__ import annotations
from typing import List, Tuple, Optional

vivian_CODE_SETTINGS_SCHEMA_URL = 'https://api-vivian.d0a.net/docs/settings-schema'

SETTING_SOURCES: Tuple[str, ...] = (
    'userSettings',
    'projectSettings',
    'localSettings',
    'flagSettings',
    'policySettings',
)

# Sources that can be edited by the user (not policy-managed)
EDITABLE_SETTING_SOURCES: Tuple[str, ...] = (
    'userSettings',
    'projectSettings',
    'localSettings',
)

SettingSource = str
EditableSettingSource = str


def getSettingSourceName(source: str) -> str:
    """Get the short name for a settings source."""
    mapping = {
        'userSettings': 'user',
        'projectSettings': 'project',
        'localSettings': 'project, gitignored',
        'flagSettings': 'cli flag',
        'policySettings': 'managed',
    }
    return mapping.get(source, source)


def getSourceDisplayName(source: str) -> str:
    """Get the short capitalized display name for a settings source."""
    mapping = {
        'userSettings': 'User',
        'projectSettings': 'Project',
        'localSettings': 'Local',
        'flagSettings': 'Flag',
        'policySettings': 'Managed',
        'plugin': 'Plugin',
        'built-in': 'Built-in',
    }
    return mapping.get(source, source.capitalize())


def getSettingSourceDisplayNameLowercase(source: str) -> str:
    """Get a lowercase display name for a settings or permission rule source."""
    mapping = {
        'userSettings': 'user settings',
        'projectSettings': 'shared project settings',
        'localSettings': 'project local settings',
        'flagSettings': 'command line arguments',
        'policySettings': 'enterprise managed settings',
        'cliArg': 'CLI argument',
        'command': 'command configuration',
        'session': 'current session',
    }
    return mapping.get(source, source)


def getSettingSourceDisplayNameCapitalized(source: str) -> str:
    """Get a capitalized display name for a settings or permission rule source."""
    lower = getSettingSourceDisplayNameLowercase(source)
    return lower[:1].upper() + lower[1:] if lower else source


def getEnabledSettingSources() -> Tuple[str, ...]:
    """Get the list of enabled setting sources for this session."""
    # In Python port, always return all sources
    return SETTING_SOURCES
