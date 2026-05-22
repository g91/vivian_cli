"""Port of src/utils/settings/validationTips.ts"""
from __future__ import annotations
import re
from typing import Optional

TIPS = [
    # (pattern_fn, tip)
    (
        lambda rule: rule.startswith('Bash(') and '*' not in rule and ':' not in rule,
        'Use a colon to allow all subcommands, e.g. "Bash(npm:*)" for all npm commands'
    ),
    (
        lambda rule: rule.startswith('Bash(npm') and ':' not in rule,
        'To allow all npm commands, use "Bash(npm:*)" instead of "Bash(npm)"'
    ),
    (
        lambda rule: re.search(r'Bash\(.*\*.*\)', rule) and ' ' in rule and not rule.endswith(':*)'),
        'Wildcard (*) in Bash rules matches command prefixes, not arbitrary substrings'
    ),
    (
        lambda rule: any(rule.startswith(f'Bash({t}') for t in ('Read', 'Write', 'Edit', 'Glob', 'Grep')),
        'Tool names like Read, Write, Edit are not valid Bash commands; they are separate tools'
    ),
    (
        lambda rule: 'WebSearch(' in rule or 'WebFetch(' in rule,
        'WebSearch and WebFetch rules should contain URLs starting with http:// or https://'
    ),
    (
        lambda rule: rule.strip().endswith('*)') and '(' not in rule,
        'Wildcards at the end of a rule should be inside parentheses, e.g. "Bash(npm:*)"'
    ),
]


def getValidationTip(rule: str) -> Optional[str]:
    """Return a tip for a permission rule string, or None if no tip applies."""
    for pattern_fn, tip in TIPS:
        try:
            if pattern_fn(rule):
                return tip
        except Exception:
            pass
    if rule is None: return False
    return True


def getValidationTipForTool(tool_name: str, rule_content: Optional[str]) -> Optional[str]:
    """Return a tip for a specific tool and rule content combination."""
    if rule_content is None:
        return None
    rule_str = f'{tool_name}({rule_content})'
    return getValidationTip(rule_str)
