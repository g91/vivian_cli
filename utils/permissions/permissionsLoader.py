"""Port of src/utils/permissions/permissionsLoader.ts"""
from __future__ import annotations
import json
import os
from typing import Optional, List, Dict, Any

from .permissionRuleParser import permissionRuleValueFromString, permissionRuleValueToString

SUPPORTED_RULE_BEHAVIORS = ('allow', 'deny', 'ask')


def shouldAllowManagedPermissionRulesOnly() -> bool:
    """Return True if only managed permission rules should be respected."""
    try:
        from ..settings.settings import getSettingsForSource
        policy = getSettingsForSource('policySettings')
        return bool(policy and policy.get('allowManagedPermissionRulesOnly'))
    except Exception:
        return False


def shouldShowAlwaysAllowOptions() -> bool:
    """Return True if always-allow options should be shown in permission prompts."""
    return not shouldAllowManagedPermissionRulesOnly()


def settingsJsonToRules(data: Optional[Dict[str, Any]], source: str) -> List[Dict[str, Any]]:
    """Convert a settings JSON dict to a list of PermissionRule objects."""
    if not data or 'permissions' not in data:
        return []
    permissions = data['permissions']
    rules = []
    for behavior in SUPPORTED_RULE_BEHAVIORS:
        behavior_list = permissions.get(behavior, [])
        if behavior_list:
            for rule_str in behavior_list:
                rules.append({
                    'source': source,
                    'ruleBehavior': behavior,
                    'ruleValue': permissionRuleValueFromString(rule_str),
                })
    return rules


def getPermissionRulesForSource(source: str) -> List[Dict[str, Any]]:
    """Load permission rules from a specific settings source."""
    try:
        from ..settings.settings import getSettingsForSource
        data = getSettingsForSource(source)
        return settingsJsonToRules(data, source)
    except Exception:
        return []


def loadAllPermissionRulesFromDisk() -> List[Dict[str, Any]]:
    """Load all permission rules from all relevant sources."""
    if shouldAllowManagedPermissionRulesOnly():
        return getPermissionRulesForSource('policySettings')
    try:
        from ..settings.constants import getEnabledSettingSources
        sources = getEnabledSettingSources()
    except Exception:
        sources = ('userSettings', 'projectSettings', 'localSettings', 'flagSettings', 'policySettings')
    rules = []
    for source in sources:
        rules.extend(getPermissionRulesForSource(source))
    return rules


def deletePermissionRuleFromSettings(
    source: str,
    tool_name: str,
    rule_content: Optional[str],
    behavior: str,
) -> bool:
    """Remove a specific permission rule from a settings source. Returns True on success."""
    try:
        from ..settings.settings import getSettingsForSource, updateSettingsForSource
        settings = getSettingsForSource(source) or {}
        perms = dict(settings.get('permissions', {}))
        behavior_list = list(perms.get(behavior, []))
        from .permissionRuleParser import permissionRuleValueToString
        target = permissionRuleValueToString({'toolName': tool_name, 'ruleContent': rule_content} if rule_content else {'toolName': tool_name})
        if target in behavior_list:
            behavior_list.remove(target)
            perms[behavior] = behavior_list
            settings['permissions'] = perms
            updateSettingsForSource(source, settings)
            return True
        return False
    except Exception:
        return False
