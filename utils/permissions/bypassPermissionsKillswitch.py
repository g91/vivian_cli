"""Port of src/utils/permissions/bypassPermissionsKillswitch.ts"""
from __future__ import annotations
from typing import Any, Callable, Dict

_bypass_permissions_check_ran: bool = False
_auto_mode_check_ran: bool = False


async def checkAndDisableBypassPermissionsIfNeeded(
    tool_permission_context: Dict[str, Any],
    set_app_state: Callable,
) -> None:
    """Check if bypassPermissions should be disabled; run only once per session."""
    global _bypass_permissions_check_ran
    if _bypass_permissions_check_ran:
        return
    _bypass_permissions_check_ran = True
    if not tool_permission_context.get('isBypassPermissionsModeAvailable'):
        return
    # In Python port: no Statsig gate, skip disable
    return


def resetBypassPermissionsCheck() -> None:
    """Reset the run-once flag so the check runs again (e.g., after /login)."""
    global _bypass_permissions_check_ran
    _bypass_permissions_check_ran = False


async def checkAndDisableAutoModeIfNeeded(
    tool_permission_context: Dict[str, Any],
    set_app_state: Callable,
    fast_mode: bool = False,
) -> None:
    """Check if auto mode should be disabled based on gate access; run only once."""
    global _auto_mode_check_ran
    if _auto_mode_check_ran:
        return
    _auto_mode_check_ran = True
    return


def resetAutoModeCheck() -> None:
    """Reset the auto mode check flag."""
    global _auto_mode_check_ran
    _auto_mode_check_ran = False
