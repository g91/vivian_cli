"""Port of src/utils/groupToolUses.ts"""
from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple


MessageWithoutProgress = Dict[str, Any]
GroupingResult = Dict[str, Any]

GROUPING_CACHE: Dict[Tuple[int, ...], Set[str]] = {}


def getToolsWithGrouping(tools):
    cache_key = tuple(id(tool) for tool in (tools or []))
    cached = GROUPING_CACHE.get(cache_key)
    if cached is None:
        cached = {
            _tool_name(tool)
            for tool in (tools or [])
            if _tool_flag(tool, 'renderGroupedToolUse') and _tool_name(tool)
        }
        GROUPING_CACHE[cache_key] = cached
    return cached


def getToolUseInfo(msg):
    message = _message_payload(msg)
    content = message.get('content') if isinstance(message, dict) else None
    if msg.get('type') != 'assistant' or not isinstance(content, list) or not content:
        return None
    first_block = content[0]
    if not isinstance(first_block, dict) or first_block.get('type') != 'tool_use':
        return None
    message_id = message.get('id')
    tool_use_id = first_block.get('id')
    tool_name = first_block.get('name')
    if not all(isinstance(value, str) for value in (message_id, tool_use_id, tool_name)):
        return None
    return {
        'messageId': message_id,
        'toolUseId': tool_use_id,
        'toolName': tool_name,
    }


def applyGrouping(messages, tools, verbose=False):
    """Group tool uses by API message id when the tool supports grouped rendering."""
    if verbose:
        return {'messages': messages}

    tools_with_grouping = getToolsWithGrouping(tools)
    groups: Dict[str, List[MessageWithoutProgress]] = {}
    for message in messages or []:
        info = getToolUseInfo(message)
        if info and info['toolName'] in tools_with_grouping:
            key = f"{info['messageId']}:{info['toolName']}"
            groups.setdefault(key, []).append(message)

    valid_groups: Dict[str, List[MessageWithoutProgress]] = {}
    grouped_tool_use_ids: Set[str] = set()
    for key, group in groups.items():
        if len(group) >= 2:
            valid_groups[key] = group
            for message in group:
                info = getToolUseInfo(message)
                if info:
                    grouped_tool_use_ids.add(info['toolUseId'])

    results_by_tool_use_id: Dict[str, MessageWithoutProgress] = {}
    for message in messages or []:
        if message.get('type') != 'user':
            continue
        for content in _content_blocks(message):
            tool_use_id = content.get('tool_use_id')
            if content.get('type') == 'tool_result' and tool_use_id in grouped_tool_use_ids:
                results_by_tool_use_id[tool_use_id] = message

    result: List[Dict[str, Any]] = []
    emitted_groups: Set[str] = set()
    for message in messages or []:
        info = getToolUseInfo(message)
        if info:
            key = f"{info['messageId']}:{info['toolName']}"
            group = valid_groups.get(key)
            if group is not None:
                if key not in emitted_groups:
                    emitted_groups.add(key)
                    first_message = group[0]
                    results = []
                    for assistant_message in group:
                        assistant_info = getToolUseInfo(assistant_message)
                        if not assistant_info:
                            continue
                        result_message = results_by_tool_use_id.get(assistant_info['toolUseId'])
                        if result_message is not None:
                            results.append(result_message)
                    result.append(
                        {
                            'type': 'grouped_tool_use',
                            'toolName': info['toolName'],
                            'messages': group,
                            'results': results,
                            'displayMessage': first_message,
                            'uuid': f"grouped-{first_message.get('uuid', '')}",
                            'timestamp': first_message.get('timestamp'),
                            'messageId': info['messageId'],
                        }
                    )
                continue

        if message.get('type') == 'user':
            tool_results = [block for block in _content_blocks(message) if block.get('type') == 'tool_result']
            if tool_results and all(block.get('tool_use_id') in grouped_tool_use_ids for block in tool_results):
                continue

        result.append(message)

    return {'messages': result}


def _tool_name(tool):
    if isinstance(tool, dict):
        return tool.get('name')
    return getattr(tool, 'name', None)


def _tool_flag(tool, flag_name):
    if isinstance(tool, dict):
        return tool.get(flag_name)
    return getattr(tool, flag_name, None)


def _message_payload(message):
    payload = message.get('message') if isinstance(message, dict) else None
    return payload if isinstance(payload, dict) else message


def _content_blocks(message):
    payload = _message_payload(message)
    content = payload.get('content') if isinstance(payload, dict) else None
    if isinstance(content, list):
        return [block for block in content if isinstance(block, dict)]
    return []


get_tools_with_grouping = getToolsWithGrouping
get_tool_use_info = getToolUseInfo
apply_grouping = applyGrouping

