"""Port of src/utils/settings/toolValidationConfig.ts"""
from __future__ import annotations
from typing import Optional, Dict, Any, Callable, Set

TOOL_VALIDATION_CONFIG: Dict[str, Dict[str, Any]] = {
    'Bash': {
        'type': 'prefix',
        'prefixSeparator': ':',
        'description': 'Shell command prefix (e.g. "npm:*" allows all npm commands)',
    },
    'Read': {
        'type': 'filePattern',
        'description': 'File glob pattern (e.g. "src/**/*.ts")',
    },
    'Write': {
        'type': 'filePattern',
        'description': 'File glob pattern (e.g. "src/**/*.ts")',
    },
    'Edit': {
        'type': 'filePattern',
        'description': 'File glob pattern (e.g. "src/**/*.ts")',
    },
    'MultiEdit': {
        'type': 'filePattern',
        'description': 'File glob pattern (e.g. "src/**/*.ts")',
    },
    'NotebookEdit': {
        'type': 'filePattern',
        'description': 'File glob pattern (e.g. "notebooks/**/*.ipynb")',
    },
    'WebSearch': {
        'type': 'exact',
        'description': 'Exact URL match (e.g. "https://example.com")',
    },
    'WebFetch': {
        'type': 'exact',
        'description': 'Exact URL match (e.g. "https://example.com")',
    },
}

FILE_PATTERN_TOOLS: Set[str] = {
    k for k, v in TOOL_VALIDATION_CONFIG.items() if v.get('type') == 'filePattern'
}

BASH_PREFIX_TOOLS: Set[str] = {
    k for k, v in TOOL_VALIDATION_CONFIG.items() if v.get('type') == 'prefix'
}


def isFilePatternTool(tool_name: str) -> bool:
    """Return True if the tool uses file-pattern based permission rules."""
    return tool_name in FILE_PATTERN_TOOLS


def isBashPrefixTool(tool_name: str) -> bool:
    """Return True if the tool uses prefix-based permission rules (like Bash)."""
    return tool_name in BASH_PREFIX_TOOLS


def getToolValidationConfig(tool_name: str) -> Optional[Dict[str, Any]]:
    """Get the validation config for a specific tool, or None if none exists."""
    return TOOL_VALIDATION_CONFIG.get(tool_name)


def getCustomValidation(tool_name: str) -> Optional[Callable[[str], Optional[str]]]:
    """Get the custom validation function for a tool, if any."""
    return TOOL_VALIDATION_CONFIG.customValidation[toolName]
