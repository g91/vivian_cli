"""Port of src/utils/permissions/permissionRuleParser.ts"""
from __future__ import annotations
from typing import Optional, List, Dict, Any

# Legacy tool name aliases for backward compatibility
LEGACY_TOOL_NAME_ALIASES: Dict[str, str] = {
    'Task': 'Agent',
    'KillShell': 'TaskStop',
    'AgentOutputTool': 'TaskOutput',
    'BashOutputTool': 'TaskOutput',
}


def normalizeLegacyToolName(name: str) -> str:
    """Normalize a potentially legacy tool name to its current canonical name."""
    return LEGACY_TOOL_NAME_ALIASES.get(name, name)


def getLegacyToolNames(canonical_name: str) -> List[str]:
    """Get all legacy names that map to the given canonical tool name."""
    return [legacy for legacy, canonical in LEGACY_TOOL_NAME_ALIASES.items() if canonical == canonical_name]


def escapeRuleContent(content: str) -> str:
    """Escape backslashes and parentheses in rule content for safe storage."""
    content = content.replace('\\', '\\\\')  # Escape backslashes first
    content = content.replace('(', '\\(')         # Escape opening parens
    content = content.replace(')', '\\)')         # Escape closing parens
    return content


def unescapeRuleContent(content: str) -> str:
    """Unescape parentheses and backslashes in rule content after parsing."""
    content = content.replace('\\(', '(')   # Unescape opening parens first
    content = content.replace('\\)', ')')   # Unescape closing parens
    content = content.replace('\\\\', '\\')  # Unescape backslashes last
    return content


def _find_first_unescaped_char(s: str, char: str) -> int:
    """Find the index of the first unescaped occurrence of char in s, or -1."""
    for i, c in enumerate(s):
        if c == char:
            backslashes = 0
            j = i - 1
            while j >= 0 and s[j] == '\\':
                backslashes += 1
                j -= 1
            if backslashes % 2 == 0:
                return i
    return -1


def _find_last_unescaped_char(s: str, char: str) -> int:
    """Find the index of the last unescaped occurrence of char in s, or -1."""
    result = -1
    for i, c in enumerate(s):
        if c == char:
            backslashes = 0
            j = i - 1
            while j >= 0 and s[j] == '\\':
                backslashes += 1
                j -= 1
            if backslashes % 2 == 0:
                result = i
    return result


def permissionRuleValueFromString(rule_string: str) -> Dict[str, Any]:
    """Parse a permission rule string like 'Bash(npm install)' into {toolName, ruleContent}."""
    open_paren = _find_first_unescaped_char(rule_string, '(')
    if open_paren == -1:
        return {'toolName': normalizeLegacyToolName(rule_string)}

    close_paren = _find_last_unescaped_char(rule_string, ')')
    if close_paren == -1 or close_paren <= open_paren:
        return {'toolName': normalizeLegacyToolName(rule_string)}

    if close_paren != len(rule_string) - 1:
        return {'toolName': normalizeLegacyToolName(rule_string)}

    tool_name = rule_string[:open_paren]
    if not tool_name:
        return {'toolName': normalizeLegacyToolName(rule_string)}

    raw_content = rule_string[open_paren + 1:close_paren]
    if raw_content == '' or raw_content == '*':
        return {'toolName': normalizeLegacyToolName(tool_name)}

    rule_content = unescapeRuleContent(raw_content)
    return {'toolName': normalizeLegacyToolName(tool_name), 'ruleContent': rule_content}


def permissionRuleValueToString(rule_value: Dict[str, Any]) -> str:
    """Convert a {toolName, ruleContent} dict to its string representation."""
    rule_content = rule_value.get('ruleContent')
    if not rule_content:
        return rule_value['toolName']
    escaped = escapeRuleContent(rule_content)
    return f"{rule_value['toolName']}({escaped})"
