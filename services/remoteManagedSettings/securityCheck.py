"""Remote managed settings security check.

Mirrors src/services/remoteManagedSettings/securityCheck.tsx.
"""
from __future__ import annotations

from typing import Any, Callable, Literal, Mapping, Optional

from ...bootstrap.state import getIsInteractive
from ...components.ManagedSettingsSecurityDialog import (
    extractDangerousSettings,
    hasDangerousSettings,
    hasDangerousSettingsChanged,
    show_managed_settings_security_dialog,
)
from ...services.analytics.index import logEvent
from ...utils.gracefulShutdown import graceful_shutdown_sync
from ...utils.settings.types import SettingsJson

SecurityCheckResult = Literal["approved", "rejected", "no_check_needed"]


def checkManagedSettingsSecurity(
    cachedSettings: Optional[Mapping[str, Any] | SettingsJson],
    newSettings: Optional[Mapping[str, Any] | SettingsJson],
    *,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> SecurityCheckResult:
    if not newSettings or not hasDangerousSettings(extractDangerousSettings(newSettings)):
        return "no_check_needed"

    if not hasDangerousSettingsChanged(cachedSettings, newSettings):
        return "no_check_needed"

    if not getIsInteractive():
        return "no_check_needed"

    logEvent("tengu_managed_settings_security_dialog_shown", {})
    result = show_managed_settings_security_dialog(
        newSettings,
        input_fn=input_fn,
        output_fn=output_fn,
    )
    if result == "approved":
        logEvent("tengu_managed_settings_security_dialog_accepted", {})
        return "approved"

    logEvent("tengu_managed_settings_security_dialog_rejected", {})
    return "rejected"


def handleSecurityCheckResult(result: SecurityCheckResult) -> bool:
    if result == "rejected":
        graceful_shutdown_sync(1)
        return False
    return True


check_managed_settings_security = checkManagedSettingsSecurity
handle_security_check_result = handleSecurityCheckResult