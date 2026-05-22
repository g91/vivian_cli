"""
passpasspass of src/utils/streamlinedTransform
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING

from ..constants.tools import (
    BASH_TOOL_NAME,
    FILE_EDIT_TOOL_NAME,
    FILE_READ_TOOL_NAME,
    FILE_WRITE_TOOL_NAME,
    GLOB_TOOL_NAME,
    GREP_TOOL_NAME,
    LSP_TOOL_NAME,
    NOTEBOOK_EDIT_TOOL_NAME,
    POWERSHELL_TOOL_NAME,
    TASK_STOP_TOOL_NAME,
    WEB_SEARCH_TOOL_NAME,
)
from ..tools.ListMcpResourcesTool.prompt import LIST_MCP_RESOURCES_TOOL_NAME
from .stringUtils import capitalize


ToolCounts = Dict[str, Any]

SEARCH_TOOLS = [GREP_TOOL_NAME, GLOB_TOOL_NAME, WEB_SEARCH_TOOL_NAME, LSP_TOOL_NAME]
READ_TOOLS = [FILE_READ_TOOL_NAME, LIST_MCP_RESOURCES_TOOL_NAME]
WRITE_TOOLS = [FILE_WRITE_TOOL_NAME, FILE_EDIT_TOOL_NAME, NOTEBOOK_EDIT_TOOL_NAME]
COMMAND_TOOLS = [BASH_TOOL_NAME, POWERSHELL_TOOL_NAME, 'Tmux', TASK_STOP_TOOL_NAME]


def _extract_text_content(content):
    if not isinstance(content, list):
        return ''
    parts = []
    for block in content:
        if isinstance(block, dict) and block.get('type') == 'text' and isinstance(block.get('text'), str):
            parts.append(block['text'])
    return '\n'.join(parts)


def categorizeToolName(toolName):
    if any(str(toolName).startswith(tool) for tool in SEARCH_TOOLS):
        return 'searches'
    if any(str(toolName).startswith(tool) for tool in READ_TOOLS):
        return 'reads'
    if any(str(toolName).startswith(tool) for tool in WRITE_TOOLS):
        return 'writes'
    if any(str(toolName).startswith(tool) for tool in COMMAND_TOOLS):
        return 'commands'
    return 'other'


def createEmptyToolCounts():
    return {
        'searches': 0,
        'reads': 0,
        'writes': 0,
        'commands': 0,
        'other': 0,
    }


def getToolSummaryText(counts):
    """Generate a summary text for tool counts."""
    parts = []
    if counts.get('searches', 0) > 0:
        count = counts['searches']
        parts.append(f"searched {count} {'pattern' if count == 1 else 'patterns'}")
    if counts.get('reads', 0) > 0:
        count = counts['reads']
        parts.append(f"read {count} {'file' if count == 1 else 'files'}")
    if counts.get('writes', 0) > 0:
        count = counts['writes']
        parts.append(f"wrote {count} {'file' if count == 1 else 'files'}")
    if counts.get('commands', 0) > 0:
        count = counts['commands']
        parts.append(f"ran {count} {'command' if count == 1 else 'commands'}")
    if counts.get('other', 0) > 0:
        count = counts['other']
        parts.append(f"{count} other {'tool' if count == 1 else 'tools'}")
    if not parts:
        return None
    return capitalize(', '.join(parts))


def accumulateToolUses(message, counts):
    """Count tool uses in an assistant message and add to existing counts."""
    payload = message.get('message') if isinstance(message, dict) else None
    content = payload.get('content') if isinstance(payload, dict) else None
    if not isinstance(content, list):
        return None
    for block in content:
        if isinstance(block, dict) and block.get('type') == 'tool_use' and isinstance(block.get('name'), str):
            category = categorizeToolName(block['name'])
            counts[category] = counts.get(category, 0) + 1
    return None


def createStreamlinedTransformer():
    """Create a stateful transformer that accumulates tool counts between text messages."""
    cumulative_counts = createEmptyToolCounts()

    def transform_to_streamlined(message):
        nonlocal cumulative_counts
        if not isinstance(message, dict):
            return None
        message_type = message.get('type')
        if message_type == 'assistant':
            payload = message.get('message') if isinstance(message.get('message'), dict) else {}
            content = payload.get('content')
            text = _extract_text_content(content).strip()
            accumulateToolUses(message, cumulative_counts)
            if text:
                cumulative_counts = createEmptyToolCounts()
                return {
                    'type': 'streamlined_text',
                    'text': text,
                    'session_id': message.get('session_id'),
                    'uuid': message.get('uuid'),
                }

            tool_summary = getToolSummaryText(cumulative_counts)
            if not tool_summary:
                return None
            return {
                'type': 'streamlined_tool_use_summary',
                'tool_summary': tool_summary,
                'session_id': message.get('session_id'),
                'uuid': message.get('uuid'),
            }

        if message_type == 'result':
            return message
        return None

    return transform_to_streamlined


def shouldIncludeInStreamlined(message):
    """Check if a message should be included in streamlined output."""
    return isinstance(message, dict) and message.get('type') in {'assistant', 'result'}


categorize_tool_name = categorizeToolName
create_empty_tool_counts = createEmptyToolCounts
get_tool_summary_text = getToolSummaryText
accumulate_tool_uses = accumulateToolUses
create_streamlined_transformer = createStreamlinedTransformer
should_include_in_streamlined = shouldIncludeInStreamlined

