"""Port of src/utils/permissions/getNextPermissionMode.ts"""
from __future__ import annotations
from typing import Optional, Dict, Any
import os


def getNextPermissionMode(tool_permission_context: Dict[str, Any], _team_context: Optional[Dict] = None) -> str:
    """Determine the next permission mode when cycling through modes with Shift+Tab."""
    mode = tool_permission_context.get('mode', 'default')
    is_bypass_available = tool_permission_context.get('isBypassPermissionsModeAvailable', False)
    is_auto_available = tool_permission_context.get('isAutoModeAvailable', False)

    if mode == 'default':
        if os.environ.get('USER_TYPE') == 'ant':
            if is_bypass_available:
                return 'bypassPermissions'
            if is_auto_available:
                return 'auto'
            return 'default'
        return 'acceptEdits'

    if mode == 'acceptEdits':
        return 'plan'

    if mode == 'plan':
        if is_bypass_available:
            return 'bypassPermissions'
        if is_auto_available:
            return 'auto'
        return 'default'

    if mode == 'bypassPermissions':
        if is_auto_available:
            return 'auto'
        return 'default'

    if mode == 'dontAsk':
        return 'default'

    # auto or any future mode -> default
    return 'default'


def cyclePermissionMode(
    tool_permission_context: Dict[str, Any],
    team_context: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Compute the next permission mode and prepare context for it."""
    next_mode = getNextPermissionMode(tool_permission_context, team_context)
    return {'nextMode': next_mode, 'context': {**tool_permission_context, 'mode': next_mode}}
