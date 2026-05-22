"""Port of src/utils/permissions/PermissionUpdate.ts"""
from __future__ import annotations
from typing import List, Dict, Any, Optional
import json
import os
from pathlib import PurePosixPath


def applyPermissionUpdate(
    context: Dict[str, Any],
    update: Dict[str, Any],
) -> Dict[str, Any]:
    """Apply a single permission update to the tool permission context."""
    if update.get('type') == 'addRules':
        rules = update.get('rules', [])
        behavior = update.get('behavior', 'allow')
        destination = update.get('destination', 'session')
        key = f'{behavior}Rules'
        current = context.get('alwaysAllowRules', {})
        existing = list(current.get(destination, []))
        from .permissionRuleParser import permissionRuleValueToString
        for rule in rules:
            rule_str = permissionRuleValueToString(rule)
            if rule_str not in existing:
                existing.append(rule_str)
        new_rules = {**current, destination: existing}
        return {**context, 'alwaysAllowRules': new_rules}
    return context


def applyPermissionUpdates(
    context: Dict[str, Any],
    updates: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Apply multiple permission updates sequentially to the context."""
    for update in updates:
        context = applyPermissionUpdate(context, update)
    return context


def persistPermissionUpdates(
    updates: List[Dict[str, Any]],
    get_settings_for_source: Any,
    update_settings_for_source: Any,
) -> None:
    """Persist permission updates to the appropriate settings files."""
    for update in updates:
        if update.get('type') != 'addRules':
            continue
        destination = update.get('destination', 'session')
        if destination == 'session':
            continue
        behavior = update.get('behavior', 'allow')
        rules = update.get('rules', [])
        try:
            settings = get_settings_for_source(destination) or {}
            perms = dict(settings.get('permissions', {}))
            behavior_list = list(perms.get(behavior, []))
            from .permissionRuleParser import permissionRuleValueToString
            for rule in rules:
                rule_str = permissionRuleValueToString(rule)
                if rule_str not in behavior_list:
                    behavior_list.append(rule_str)
            perms[behavior] = behavior_list
            settings['permissions'] = perms
            update_settings_for_source(destination, settings)
        except Exception:
            pass


def createReadRuleSuggestion(
    dir_path: str,
    destination: str = 'session',
) -> Optional[Dict[str, Any]]:
    """Create a suggestion to add a Read rule for a directory."""
    path_for_pattern = str(PurePosixPath(dir_path.replace(os.sep, '/')))
    if path_for_pattern == '/':
        return None
    rule_content = f"/{path_for_pattern}/**" if path_for_pattern.startswith('/') else f"{path_for_pattern}/**"
    return {
        'type': 'addRules',
        'rules': [{'toolName': 'Read', 'ruleContent': rule_content}],
        'behavior': 'allow',
        'destination': destination,
    }
