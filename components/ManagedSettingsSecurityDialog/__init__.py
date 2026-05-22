"""ManagedSettingsSecurityDialog component package."""

from .ManagedSettingsSecurityDialog import ManagedSettingsSecurityDialog, show_managed_settings_security_dialog
from .utils import (
    DangerousSettings,
    extractDangerousSettings,
    extract_dangerous_settings,
    formatDangerousSettingsList,
    format_dangerous_settings_list,
    hasDangerousSettings,
    hasDangerousSettingsChanged,
    has_dangerous_settings,
    has_dangerous_settings_changed,
)

__all__ = [
    "DangerousSettings",
    "ManagedSettingsSecurityDialog",
    "extractDangerousSettings",
    "extract_dangerous_settings",
    "formatDangerousSettingsList",
    "format_dangerous_settings_list",
    "hasDangerousSettings",
    "hasDangerousSettingsChanged",
    "has_dangerous_settings",
    "has_dangerous_settings_changed",
    "show_managed_settings_security_dialog",
]