"""Port of src/utils/settings/permissionValidation.ts"""
from __future__ import annotations
from typing import Optional, Dict, Any, List

from .toolValidationConfig import isFilePatternTool, isBashPrefixTool, getToolValidationConfig
from .validation import validatePermissionRuleString


def validatePermissionRule(tool_name: str, rule_content: Optional[str]) -> Optional[str]:
    """Validate a permission rule for a specific tool.
    Returns an error message string on failure, or None on success."""
    config = getToolValidationConfig(tool_name)
    if config is None:
        return None  # Unknown tool - no validation

    if rule_content is None or rule_content == '':
        return None  # Tool-wide permission - always valid

    err = validatePermissionRuleString(rule_content)
    if err:
        return err

    rule_type = config.get('type', 'exact')

    if rule_type == 'filePattern':
        # Validate as a glob pattern - must not be an absolute Windows path with wrong separator
        if '\\' in rule_content and ':' in rule_content:
            return 'Use forward slashes in file patterns'
        return None

    if rule_type == 'prefix':
        # Bash prefix: may contain colon separator
        return None

    if rule_type == 'exact':
        # Exact match - validate URL-like tools
        if tool_name in ('WebSearch', 'WebFetch'):
            if rule_content != '*' and not rule_content.startswith(('http://', 'https://')):
                return 'URL must start with http:// or https://'
        return None

    return None


def validatePermissionRules(
    rules: List[str],
    tool_name: str,
) -> Dict[str, Any]:
    """Validate a list of permission rules for a tool. Returns {valid, invalid, errors}."""
    valid = []
    invalid = []
    errors = []
    for rule in rules:
        from ..permissions.permissionRuleParser import permissionRuleValueFromString
        parsed = permissionRuleValueFromString(rule)
        actual_tool = parsed.get('toolName', tool_name)
        content = parsed.get('ruleContent')
        err = validatePermissionRule(actual_tool, content)
        if err is None:
            valid.append(rule)
        else:
            invalid.append(rule)
            errors.append({'rule': rule, 'error': err})
    return {'valid': valid, 'invalid': invalid, 'errors': errors}
