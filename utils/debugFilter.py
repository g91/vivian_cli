"""
Port of src/utils/debugFilter.ts
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
import re
import logging
from collections import defaultdict
from functools import lru_cache, wraps


DebugFilter = Dict[str, Any]


@lru_cache(maxsize=None)
def parseDebugFilter(filterString=None):
    """Parse debug filter string into include/exclude category rules."""
    if not filterString or not str(filterString).strip():
        return None

    filters = [part.strip() for part in str(filterString).split(',') if part.strip()]
    if not filters:
        return None

    has_exclusive = any(part.startswith('!') for part in filters)
    has_inclusive = any(not part.startswith('!') for part in filters)
    if has_exclusive and has_inclusive:
        return None

    clean_filters = [re.sub(r'^!', '', part).lower() for part in filters]
    return {
        'include': [] if has_exclusive else clean_filters,
        'exclude': clean_filters if has_exclusive else [],
        'isExclusive': has_exclusive,
    }


def extractDebugCategories(message):
    """Extract debug categories from a message"""
    categories: List[str] = []
    message_text = '' if message is None else str(message)

    mcp_match = re.match(r'^MCP server ["\']([^"\']+)["\']', message_text)
    if mcp_match and mcp_match.group(1):
        categories.append('mcp')
        categories.append(mcp_match.group(1).lower())
    else:
        prefix_match = re.match(r'^([^:\[]+):', message_text)
        if prefix_match and prefix_match.group(1):
            categories.append(prefix_match.group(1).strip().lower())

    bracket_match = re.match(r'^\[([^\]]+)]', message_text)
    if bracket_match and bracket_match.group(1):
        categories.append(bracket_match.group(1).strip().lower())

    if '1p event:' in message_text.lower():
        categories.append('1p')

    secondary_match = re.search(r':\s*([^:]+?)(?:\s+(?:type|mode|status|event))?:', message_text)
    if secondary_match and secondary_match.group(1):
        secondary = secondary_match.group(1).strip().lower()
        if len(secondary) < 30 and ' ' not in secondary:
            categories.append(secondary)

    seen = set()
    result = []
    for category in categories:
        if category not in seen:
            seen.add(category)
            result.append(category)
    return result


def shouldShowDebugCategories(categories, filter):
    """Check if debug message should be shown based on filter"""
    if not filter:
        return True
    if not categories:
        return False
    if filter.get('isExclusive'):
        return not any(category in (filter.get('exclude') or []) for category in categories)
    return any(category in (filter.get('include') or []) for category in categories)


def shouldShowDebugMessage(message, filter):
    """Main function to check if a debug message should be shown"""
    if not filter:
        return True
    categories = extractDebugCategories(message)
    return shouldShowDebugCategories(categories, filter)


parse_debug_filter = parseDebugFilter
extract_debug_categories = extractDebugCategories
should_show_debug_categories = shouldShowDebugCategories
should_show_debug_message = shouldShowDebugMessage

