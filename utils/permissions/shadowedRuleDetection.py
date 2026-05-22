"""Port of src/utils/permissions/shadowedRuleDetection.ts"""
from __future__ import annotations
from typing import List, Dict, Any, Optional, Tuple


def isSharedSettingSource(source: str) -> bool:
    """Return True if the setting source is shared (visible to other users)."""
    return source in ('projectSettings', 'policySettings', 'command')


def detectUnreachableRules(
    allow_rules: List[Dict[str, Any]],
    ask_rules: List[Dict[str, Any]],
    deny_rules: List[Dict[str, Any]],
    options: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Detect permission rules that are unreachable due to shadowing by ask/deny rules."""
    options = options or {}
    sandbox_auto_allow = options.get('sandboxAutoAllowEnabled', False)
    unreachable = []
    bash_tool = 'Bash'

    for allow_rule in allow_rules:
        rule_value = allow_rule.get('ruleValue', {})
        tool_name = rule_value.get('toolName', '')
        rule_content = rule_value.get('ruleContent')
        if rule_content is None:
            # Tool-wide allow can't be shadowed by ask
            continue
        # Check shadowing by deny rules (tool-wide deny blocks specific allow)
        for deny_rule in deny_rules:
            deny_value = deny_rule.get('ruleValue', {})
            if (deny_value.get('toolName') == tool_name and
                    deny_value.get('ruleContent') is None):
                unreachable.append({
                    'rule': allow_rule,
                    'shadowedBy': deny_rule,
                    'shadowType': 'deny',
                    'reason': f'Tool-wide deny rule shadows specific allow rule for {tool_name}',
                    'fix': f'Remove the {tool_name} deny rule or the specific allow rule',
                })
                break
        # Check shadowing by ask rules (tool-wide ask blocks specific allow, unless sandboxed)
        for ask_rule in ask_rules:
            ask_value = ask_rule.get('ruleValue', {})
            if (ask_value.get('toolName') == tool_name and
                    ask_value.get('ruleContent') is None):
                # Skip if sandbox auto-allow and personal settings source
                if (tool_name == bash_tool and sandbox_auto_allow and
                        not isSharedSettingSource(ask_rule.get('source', ''))):
                    continue
                unreachable.append({
                    'rule': allow_rule,
                    'shadowedBy': ask_rule,
                    'shadowType': 'ask',
                    'reason': f'Tool-wide ask rule shadows specific allow rule for {tool_name}',
                    'fix': f'Remove the {tool_name} ask rule or the specific allow rule',
                })
                break
    return unreachable
