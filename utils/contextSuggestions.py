"""
passpasspass of src/utils/contextSuggestions
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Literal, Optional

from ..constants.tools import BASH_TOOL_NAME, FILE_READ_TOOL_NAME, GREP_TOOL_NAME, WEB_FETCH_TOOL_NAME


SuggestionSeverity = Literal['info', 'warning']
ContextSuggestion = Dict[str, Any]


LARGE_TOOL_RESULT_PERCENT = 15
LARGE_TOOL_RESULT_TOKENS = 10_000
READ_BLOAT_PERCENT = 5
NEAR_CAPACITY_PERCENT = 80
MEMORY_HIGH_PERCENT = 5
MEMORY_HIGH_TOKENS = 5_000


def _format_tokens(tokens: int) -> str:
    if tokens >= 1_000_000:
        return f'{tokens / 1_000_000:.1f}M'
    if tokens >= 1_000:
        return f'{tokens / 1_000:.1f}K'
    return str(tokens)


def _display_path(file_path: str) -> str:
    return os.path.basename(file_path.rstrip(os.sep)) or file_path


def generateContextSuggestions(data):
    suggestions: list[ContextSuggestion] = []

    checkNearCapacity(data, suggestions)
    checkLargeToolResults(data, suggestions)
    checkReadResultBloat(data, suggestions)
    checkMemoryBloat(data, suggestions)
    checkAutoCompactDisabled(data, suggestions)

    suggestions.sort(
        key=lambda item: (
            0 if item.get('severity') == 'warning' else 1,
            -(item.get('savingsTokens') or 0),
        )
    )
    return suggestions


def checkNearCapacity(data, suggestions):
    percentage = getattr(data, 'percentage', None) if not isinstance(data, dict) else data.get('percentage')
    if percentage is None:
        return
    if percentage >= NEAR_CAPACITY_PERCENT:
        is_auto_compact_enabled = (
            getattr(data, 'isAutoCompactEnabled', False)
            if not isinstance(data, dict)
            else data.get('isAutoCompactEnabled', False)
        )
        suggestions.append(
            {
                'severity': 'warning',
                'title': f'Context is {percentage}% full',
                'detail': (
                    'Autocompact will trigger soon, which discards older messages. Use /compact now to control what gets kept.'
                    if is_auto_compact_enabled
                    else 'Autocompact is disabled. Use /compact to free space, or enable autocompact in /config.'
                ),
            }
        )


def checkLargeToolResults(data, suggestions):
    message_breakdown = data.get('messageBreakdown') if isinstance(data, dict) else getattr(data, 'messageBreakdown', None)
    if not message_breakdown:
        return
    tool_calls = message_breakdown.get('toolCallsByType') if isinstance(message_breakdown, dict) else getattr(message_breakdown, 'toolCallsByType', [])
    raw_max_tokens = data.get('rawMaxTokens') if isinstance(data, dict) else getattr(data, 'rawMaxTokens', 0)
    for tool in tool_calls:
        call_tokens = tool.get('callTokens') if isinstance(tool, dict) else getattr(tool, 'callTokens', 0)
        result_tokens = tool.get('resultTokens') if isinstance(tool, dict) else getattr(tool, 'resultTokens', 0)
        totalToolTokens = call_tokens + result_tokens
        percent = (totalToolTokens / raw_max_tokens) * 100 if raw_max_tokens else 0
        if (
        percent < LARGE_TOOL_RESULT_PERCENT or
        totalToolTokens < LARGE_TOOL_RESULT_TOKENS
        ):
            continue
        suggestion = getLargeToolSuggestion(
        tool.get('name') if isinstance(tool, dict) else getattr(tool, 'name', ''),
        totalToolTokens,
        percent,
        )
        if suggestion:
            suggestions.append(suggestion)


def getLargeToolSuggestion(toolName, tokens, percent):
    token_str = _format_tokens(tokens)
    if toolName == BASH_TOOL_NAME:
        return {
            'severity': 'warning',
            'title': f'Bash results using {token_str} tokens ({percent:.0f}%)',
            'detail': 'Pipe output through head, tail, or grep to reduce result size. Avoid cat on large files - use Read with offset/limit instead.',
            'savingsTokens': int(tokens * 0.5),
        }
    if toolName == FILE_READ_TOOL_NAME:
        return {
            'severity': 'info',
            'title': f'Read results using {token_str} tokens ({percent:.0f}%)',
            'detail': 'Use offset and limit parameters to read only the sections you need. Avoid re-reading entire files when you only need a few lines.',
            'savingsTokens': int(tokens * 0.3),
        }
    if toolName == GREP_TOOL_NAME:
        return {
            'severity': 'info',
            'title': f'Grep results using {token_str} tokens ({percent:.0f}%)',
            'detail': 'Add more specific patterns or use the glob or type parameter to narrow file types. Consider Glob for file discovery instead of Grep.',
            'savingsTokens': int(tokens * 0.3),
        }
    if toolName == WEB_FETCH_TOOL_NAME:
        return {
            'severity': 'info',
            'title': f'WebFetch results using {token_str} tokens ({percent:.0f}%)',
            'detail': 'Web page content can be very large. Consider extracting only the specific information needed.',
            'savingsTokens': int(tokens * 0.4),
        }
    if percent >= 20:
        return {
            'severity': 'info',
            'title': f'{toolName} using {token_str} tokens ({percent:.0f}%)',
            'detail': 'This tool is consuming a significant portion of context.',
            'savingsTokens': int(tokens * 0.2),
        }
    return None


def checkReadResultBloat(data, suggestions):
    message_breakdown = data.get('messageBreakdown') if isinstance(data, dict) else getattr(data, 'messageBreakdown', None)
    if not message_breakdown:
        return
    tool_calls = message_breakdown.get('toolCallsByType') if isinstance(message_breakdown, dict) else getattr(message_breakdown, 'toolCallsByType', [])
    read_tool = None
    for tool in tool_calls:
        name = tool.get('name') if isinstance(tool, dict) else getattr(tool, 'name', None)
        if name == FILE_READ_TOOL_NAME:
            read_tool = tool
            break
    if not read_tool:
        return

    raw_max_tokens = data.get('rawMaxTokens') if isinstance(data, dict) else getattr(data, 'rawMaxTokens', 0)
    call_tokens = read_tool.get('callTokens') if isinstance(read_tool, dict) else getattr(read_tool, 'callTokens', 0)
    result_tokens = read_tool.get('resultTokens') if isinstance(read_tool, dict) else getattr(read_tool, 'resultTokens', 0)
    total_read_tokens = call_tokens + result_tokens
    total_read_percent = (total_read_tokens / raw_max_tokens) * 100 if raw_max_tokens else 0
    read_percent = (result_tokens / raw_max_tokens) * 100 if raw_max_tokens else 0

    if total_read_percent >= LARGE_TOOL_RESULT_PERCENT and total_read_tokens >= LARGE_TOOL_RESULT_TOKENS:
        return
    if read_percent >= READ_BLOAT_PERCENT and result_tokens >= LARGE_TOOL_RESULT_TOKENS:
        suggestions.append(
            {
                'severity': 'info',
                'title': f'File reads using {_format_tokens(result_tokens)} tokens ({read_percent:.0f}%)',
                'detail': 'If you are re-reading files, consider referencing earlier reads. Use offset/limit for large files.',
                'savingsTokens': int(result_tokens * 0.3),
            }
        )


def checkMemoryBloat(data, suggestions):
    memory_files = data.get('memoryFiles') if isinstance(data, dict) else getattr(data, 'memoryFiles', [])
    raw_max_tokens = data.get('rawMaxTokens') if isinstance(data, dict) else getattr(data, 'rawMaxTokens', 0)
    total_memory_tokens = 0
    for item in memory_files or []:
        total_memory_tokens += item.get('tokens', 0) if isinstance(item, dict) else getattr(item, 'tokens', 0)
    memory_percent = (total_memory_tokens / raw_max_tokens) * 100 if raw_max_tokens else 0

    if memory_percent >= MEMORY_HIGH_PERCENT and total_memory_tokens >= MEMORY_HIGH_TOKENS:
        largest = sorted(
            memory_files or [],
            key=lambda item: item.get('tokens', 0) if isinstance(item, dict) else getattr(item, 'tokens', 0),
            reverse=True,
        )[:3]
        largest_files = ', '.join(
            f"{_display_path(item.get('path') if isinstance(item, dict) else getattr(item, 'path', ''))} ({_format_tokens(item.get('tokens', 0) if isinstance(item, dict) else getattr(item, 'tokens', 0))})"
            for item in largest
        )
        suggestions.append(
            {
                'severity': 'info',
                'title': f'Memory files using {_format_tokens(total_memory_tokens)} tokens ({memory_percent:.0f}%)',
                'detail': f'Largest: {largest_files}. Use /memory to review and prune stale entries.',
                'savingsTokens': int(total_memory_tokens * 0.3),
            }
        )


def checkAutoCompactDisabled(data, suggestions):
    percentage = data.get('percentage') if isinstance(data, dict) else getattr(data, 'percentage', None)
    is_auto_compact_enabled = (
        getattr(data, 'isAutoCompactEnabled', False)
        if not isinstance(data, dict)
        else data.get('isAutoCompactEnabled', False)
    )
    if percentage is None:
        return
    if not is_auto_compact_enabled and percentage >= 50 and percentage < NEAR_CAPACITY_PERCENT:
        suggestions.append(
            {
                'severity': 'info',
                'title': 'Autocompact is disabled',
                'detail': 'Without autocompact, you will hit context limits and lose the conversation. Enable it in /config or use /compact manually.',
            }
        )


generate_context_suggestions = generateContextSuggestions
check_near_capacity = checkNearCapacity
check_large_tool_results = checkLargeToolResults
get_large_tool_suggestion = getLargeToolSuggestion
check_read_result_bloat = checkReadResultBloat
check_memory_bloat = checkMemoryBloat
check_auto_compact_disabled = checkAutoCompactDisabled

