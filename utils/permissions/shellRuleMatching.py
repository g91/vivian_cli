"""Port of src/utils/permissions/shellRuleMatching.ts"""
from __future__ import annotations
import re
from typing import Optional, List, Dict, Any

_ESCAPED_STAR_PH = '__ESCAPED_STAR__'
_ESCAPED_BACKSLASH_PH = '__ESCAPED_BACKSLASH__'
_ESCAPED_STAR_RE = re.compile(re.escape(_ESCAPED_STAR_PH))
_ESCAPED_BACKSLASH_RE = re.compile(re.escape(_ESCAPED_BACKSLASH_PH))


def permissionRuleExtractPrefix(permission_rule: str) -> Optional[str]:
    """Extract prefix from legacy :* syntax (e.g., 'npm:*' -> 'npm')."""
    m = re.match(r'^(.+):\*$', permission_rule)
    return m.group(1) if m else None


def hasWildcards(pattern: str) -> bool:
    """Check if a pattern contains unescaped wildcards (not legacy :* syntax)."""
    if pattern.endswith(':*'):
        return False
    backslash_count = 0
    for ch in pattern:
        if ch == '\\':
            backslash_count += 1
        elif ch == '*':
            if backslash_count % 2 == 0:
                return True
            backslash_count = 0
        else:
            backslash_count = 0
    return False


def matchWildcardPattern(pattern: str, command: str, case_insensitive: bool = False) -> bool:
    """Match a command against a wildcard pattern. Wildcards (*) match any sequence."""
    trimmed = pattern.strip()
    processed = ''
    i = 0
    while i < len(trimmed):
        ch = trimmed[i]
        if ch == '\\' and i + 1 < len(trimmed):
            next_ch = trimmed[i + 1]
            if next_ch == '*':
                processed += _ESCAPED_STAR_PH
                i += 2
                continue
            elif next_ch == '\\':
                processed += _ESCAPED_BACKSLASH_PH
                i += 2
                continue
        processed += ch
        i += 1

    # Escape regex special chars
    escaped = re.sub(r'([.+?^${}()|\[\]\\])', r'\\\\1', processed)
    # Convert unescaped * to .*
    with_wildcards = escaped.replace('*', '.*')
    # Restore placeholders
    regex_pattern = _ESCAPED_STAR_RE.sub('\\\\*', with_wildcards)
    regex_pattern = _ESCAPED_BACKSLASH_RE.sub('\\\\\\\\', regex_pattern)

    # Make trailing ' *' optional when it's the only wildcard
    unescaped_star_count = processed.count('*')
    if regex_pattern.endswith(' .*') and unescaped_star_count == 1:
        regex_pattern = regex_pattern[:-3] + '( .*)?'

    flags = re.DOTALL | (re.IGNORECASE if case_insensitive else 0)
    try:
        return bool(re.match('^' + regex_pattern + '$', command, flags))
    except re.error:
        return False


def parsePermissionRule(permission_rule: str) -> Dict[str, Any]:
    """Parse a permission rule string into a structured rule dict with type field."""
    prefix = permissionRuleExtractPrefix(permission_rule)
    if prefix is not None:
        return {'type': 'prefix', 'prefix': prefix}
    if hasWildcards(permission_rule):
        return {'type': 'wildcard', 'pattern': permission_rule}
    return {'type': 'exact', 'command': permission_rule}


def suggestionForExactCommand(tool_name: str, command: str) -> List[Dict[str, Any]]:
    """Generate permission update suggestion for an exact command match."""
    return [{
        'type': 'addRules',
        'rules': [{'toolName': tool_name, 'ruleContent': command}],
        'behavior': 'allow',
        'destination': 'localSettings',
    }]


def suggestionForPrefix(tool_name: str, prefix: str) -> List[Dict[str, Any]]:
    """Generate permission update suggestion for a prefix match."""
    return [{
        'type': 'addRules',
        'rules': [{'toolName': tool_name, 'ruleContent': prefix + ':*'}],
        'behavior': 'allow',
        'destination': 'localSettings',
    }]
