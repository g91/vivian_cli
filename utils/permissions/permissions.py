"""Port of src/utils/permissions/permissions.ts"""
from __future__ import annotations
import os
from typing import Optional, List, Dict, Any, Tuple

from .permissionRuleParser import permissionRuleValueFromString, permissionRuleValueToString
from .PermissionMode import permissionModeTitle


def permissionRuleSourceDisplayString(source: str) -> str:
    """Get a human-readable display string for a permission rule source."""
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


def getAllowRules(context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get all allow rules from a tool permission context."""
    sources = ('userSettings', 'projectSettings', 'localSettings', 'flagSettings', 'policySettings', 'cliArg', 'command', 'session')
    rules = []
    always_allow = context.get('alwaysAllowRules', {})
    for source in sources:
        source_rules = always_allow.get(source, [])
        for rule_str in source_rules:
            rules.append({
                'source': source,
                'ruleBehavior': 'allow',
                'ruleValue': permissionRuleValueFromString(rule_str),
            })
    return rules


def getDenyRules(context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get all deny rules from a tool permission context."""
    sources = ('userSettings', 'projectSettings', 'localSettings', 'flagSettings', 'policySettings', 'cliArg', 'command', 'session')
    rules = []
    always_deny = context.get('alwaysDenyRules', {})
    for source in sources:
        source_rules = always_deny.get(source, [])
        for rule_str in source_rules:
            rules.append({
                'source': source,
                'ruleBehavior': 'deny',
                'ruleValue': permissionRuleValueFromString(rule_str),
            })
    return rules


def getAskRules(context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get all ask rules from a tool permission context."""
    sources = ('userSettings', 'projectSettings', 'localSettings', 'flagSettings', 'policySettings', 'cliArg', 'command', 'session')
    rules = []
    always_ask = context.get('alwaysAskRules', {})
    for source in sources:
        source_rules = always_ask.get(source, [])
        for rule_str in source_rules:
            rules.append({
                'source': source,
                'ruleBehavior': 'ask',
                'ruleValue': permissionRuleValueFromString(rule_str),
            })
    return rules


def createPermissionRequestMessage(tool_name: str, decision_reason: Optional[Dict[str, Any]] = None) -> str:
    """Create a human-readable permission request message."""
    if not decision_reason:
        return f'Permission required for {tool_name} command'

    reason_type = decision_reason.get('type', '')

    if reason_type == 'hook':
        hook_name = decision_reason.get('hookName', 'unknown')
        reason = decision_reason.get('reason', '')
        if reason:
            return f"Hook '{hook_name}' blocked this action: {reason}"
        return f"Hook '{hook_name}' requires approval for this {tool_name} command"

    if reason_type == 'rule':
        rule = decision_reason.get('rule', {})
        rule_str = permissionRuleValueToString(rule.get('ruleValue', {'toolName': tool_name}))
        source_str = permissionRuleSourceDisplayString(rule.get('source', ''))
        return f"Permission rule '{rule_str}' from {source_str} requires approval for this {tool_name} command"

    if reason_type == 'mode':
        mode_title = permissionModeTitle(decision_reason.get('mode', 'default'))
        return f"Current permission mode ({mode_title}) requires approval for this {tool_name} command"

    if reason_type == 'subcommandResults':
        reasons = decision_reason.get('reasons', [])
        parts = [cmd for cmd, r in reasons if r.get('behavior') in ('ask', 'passthrough')]
        if parts:
            n = len(parts)
            word = 'part' if n == 1 else 'parts'
            req = 'requires' if n == 1 else 'require'
            return f"This {tool_name} command contains multiple operations. The following {n} {word} {req} approval: {', '.join(parts)}"
        return f"This {tool_name} command contains multiple operations that require approval"

    if reason_type == 'permissionPromptTool':
        pt_name = decision_reason.get('permissionPromptToolName', '')
        return f"Tool '{pt_name}' requires approval for this {tool_name} command"

    if reason_type == 'sandboxOverride':
        return 'Run outside of the sandbox'

    reason_text = decision_reason.get('reason', f'Permission required for {tool_name}')
    return reason_text


def getRuleByContentsForToolName(
    context: Dict[str, Any],
    tool_name: str,
    rule_content: Optional[str],
    behavior: str = 'allow',
) -> Optional[Dict[str, Any]]:
    """Find a permission rule matching the given tool name and content."""
    if behavior == 'allow':
        rules = getAllowRules(context)
    elif behavior == 'deny':
        rules = getDenyRules(context)
    else:
        rules = getAskRules(context)
    for rule in rules:
        rv = rule.get('ruleValue', {})
        if rv.get('toolName') == tool_name and rv.get('ruleContent') == rule_content:
            return rule
    return None


def applyPermissionRulesToPermissionContext(
    context: Dict[str, Any],
    rules: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Apply loaded permission rules to the permission context."""
    always_allow = dict(context.get('alwaysAllowRules', {}))
    always_deny = dict(context.get('alwaysDenyRules', {}))
    always_ask = dict(context.get('alwaysAskRules', {}))

    for rule in rules:
        source = rule.get('source', 'session')
        behavior = rule.get('ruleBehavior', 'allow')
        rule_str = permissionRuleValueToString(rule.get('ruleValue', {'toolName': ''}))

        if behavior == 'allow':
            lst = list(always_allow.get(source, []))
            if rule_str not in lst:
                lst.append(rule_str)
            always_allow[source] = lst
        elif behavior == 'deny':
            lst = list(always_deny.get(source, []))
            if rule_str not in lst:
                lst.append(rule_str)
            always_deny[source] = lst
        elif behavior == 'ask':
            lst = list(always_ask.get(source, []))
            if rule_str not in lst:
                lst.append(rule_str)
            always_ask[source] = lst

    return {
        **context,
        'alwaysAllowRules': always_allow,
        'alwaysDenyRules': always_deny,
        'alwaysAskRules': always_ask,
    }
