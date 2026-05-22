"""Port of src/utils/settings/types.ts"""
from __future__ import annotations
from typing import Optional, List, Dict, Any, Literal
try:
    from typing import TypedDict, NotRequired
except ImportError:
    from typing_extensions import TypedDict, NotRequired


class PermissionsSettings(TypedDict, total=False):
    allow: List[str]
    deny: List[str]
    ask: List[str]


class SettingsJson(TypedDict, total=False):
    """The shape of a vivian Code settings.json file."""
    model: str
    permissions: PermissionsSettings
    apiKeyHelper: str
    env: Dict[str, str]
    includeCoAuthoredBy: bool
    cleanupPeriodDays: int
    preferredNotifChannel: str
    autoUpdaterStatus: str
    theme: str
    verbose: bool
    maxFileReads: int
    enabledMcpjsonServers: Optional[List[str]]
    disabledMcpjsonServers: Optional[List[str]]
    disableAllMcpjsonServers: bool
    allowManagedPermissionRulesOnly: bool
    hasTrustDialogAccepted: bool
    projects: Dict[str, Any]
    mcpServers: Dict[str, Any]
    customApiKeyResponses: Dict[str, str]


class LocalSettingsJson(TypedDict, total=False):
    """The shape of a vivian Code settings.local.json file."""
    permissions: PermissionsSettings
    excludeFromGitignoreCheck: bool


class FullSettingsContext(TypedDict, total=False):
    """Merged context of all settings sources for the current session."""
    userSettings: SettingsJson
    projectSettings: SettingsJson
    localSettings: LocalSettingsJson
    flagSettings: SettingsJson
    policySettings: SettingsJson
    mergedSettings: SettingsJson


SettingsSource = Literal[
    'userSettings', 'projectSettings', 'localSettings', 'flagSettings', 'policySettings'
]
EditableSettingSource = Literal['userSettings', 'projectSettings', 'localSettings']
