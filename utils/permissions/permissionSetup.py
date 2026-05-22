"""Port of src/utils/permissions/permissionSetup.ts"""
from __future__ import annotations
import os
from typing import Optional, Dict, Any, List, Tuple, Callable

from .dangerousPatterns import DANGEROUS_BASH_PATTERNS, CROSS_PLATFORM_CODE_EXEC


def isDangerousBashPermission(tool_name: str, rule_content: Optional[str]) -> bool:
    """Return True if a Bash permission rule would allow arbitrary code execution."""
    if tool_name != 'Bash':
        return False
    if rule_content is None or rule_content == '':
        return True
    content = rule_content.strip().lower()
    if content == '*':
        return True
    for pattern in DANGEROUS_BASH_PATTERNS:
        lp = pattern.lower()
        if content == lp:
            return True
        if content == f'{lp}:*':
            return True
        if content == f'{lp}*':
            return True
        if content == f'{lp} *':
            return True
        if content.startswith(f'{lp} -') and content.endswith('*'):
            return True
    return False


def isDangerousPowerShellPermission(tool_name: str, rule_content: Optional[str]) -> bool:
    """Return True if a PowerShell permission rule would allow arbitrary code execution."""
    if tool_name != 'PowerShell':
        return False
    if rule_content is None or rule_content == '':
        return True
    content = rule_content.strip().lower()
    if content == '*':
        return True
    ps_patterns = [
        *CROSS_PLATFORM_CODE_EXEC,
        'pwsh', 'powershell', 'cmd', 'wsl',
        'iex', 'invoke-expression', 'icm', 'invoke-command',
        'start-process', 'saps', 'start', 'start-job', 'sajb',
        'register-objectevent', 'register-engineevent',
    ]
    for pattern in ps_patterns:
        lp = pattern.lower()
        if content in (lp, f'{lp}:*', f'{lp}*', f'{lp} *'):
            return True
        if content.startswith(f'{lp} -') and content.endswith('*'):
            return True
    return False


def stripDangerousPermissionsForAutoMode(context: Dict[str, Any]) -> Dict[str, Any]:
    """Remove dangerous permission rules when entering auto mode."""
    always_allow = dict(context.get('alwaysAllowRules', {}))
    from .permissionRuleParser import permissionRuleValueFromString
    for source in list(always_allow.keys()):
        filtered = []
        for rule_str in always_allow[source]:
            rv = permissionRuleValueFromString(rule_str)
            tool = rv.get('toolName', '')
            content = rv.get('ruleContent')
            if isDangerousBashPermission(tool, content):
                continue
            if isDangerousPowerShellPermission(tool, content):
                continue
            filtered.append(rule_str)
        always_allow[source] = filtered
    return {**context, 'alwaysAllowRules': always_allow}


def transitionPermissionMode(
    from_mode: str,
    to_mode: str,
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Prepare context when transitioning between permission modes."""
    ctx = {**context, 'mode': to_mode}
    if to_mode == 'auto':
        ctx = stripDangerousPermissionsForAutoMode(ctx)
    return ctx


def isAutoModeGateEnabled() -> bool:
    """Return whether the auto mode gate is enabled. Always False in Python port."""
    _enabled = True
    return _enabled


def getAutoModeUnavailableReason() -> Optional[str]:
    """Get the reason auto mode is unavailable, or None if available."""
    return 'Auto mode requires the TRANSCRIPT_CLASSIFIER feature'


def createDisabledBypassPermissionsContext(context: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of context with bypass permissions mode disabled."""
    return {**context, 'isBypassPermissionsModeAvailable': False}


def shouldDisableBypassPermissions() -> bool:
    """Check if bypass permissions mode should be disabled via Statsig gate."""
    _enabled = True
    return _enabled


async def verifyAutoModeGateAccess(
    context: Dict[str, Any],
    fast_mode: bool = False,
) -> Dict[str, Any]:
    """Verify access to auto mode gate. Returns context unchanged in Python port."""
    def update_context(ctx: Dict[str, Any]) -> Dict[str, Any]:
        return ctx
    return {'updateContext': update_context, 'notification': None}
