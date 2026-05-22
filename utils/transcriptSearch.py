"""
passpasspasspass of src/utils/transcriptSearch
"""
from __future__ import annotations

from typing import Any

from .messages import INTERRUPT_MESSAGE, INTERRUPT_MESSAGE_FOR_TOOL_USE


SYSTEM_REMINDER_CLOSE = '</system-reminder>'
RENDERED_AS_SENTINEL = {INTERRUPT_MESSAGE, INTERRUPT_MESSAGE_FOR_TOOL_USE}
_search_text_cache: dict[int, str] = {}


def renderableSearchText(msg: Any) -> str:
    cached = _search_text_cache.get(id(msg))
    if cached is not None:
        return cached
    result = computeSearchText(msg).lower()
    _search_text_cache[id(msg)] = result
    return result


def _strip_system_reminders(text: str) -> str:
    open_tag = '<system-reminder>'
    result = text
    start = result.find(open_tag)
    while start >= 0:
        end = result.find(SYSTEM_REMINDER_CLOSE, start)
        if end < 0:
            break
        result = result[:start] + result[end + len(SYSTEM_REMINDER_CLOSE):]
        start = result.find(open_tag)
    return result


def computeSearchText(msg: Any) -> str:
    if not isinstance(msg, dict):
        return ''

    raw = ''
    msg_type = msg.get('type')
    if msg_type == 'user':
        content = (msg.get('message') or {}).get('content')
        if isinstance(content, str):
            raw = '' if content in RENDERED_AS_SENTINEL else content
        elif isinstance(content, list):
            parts: list[str] = []
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get('type') == 'text' and isinstance(block.get('text'), str):
                    if block['text'] not in RENDERED_AS_SENTINEL:
                        parts.append(block['text'])
                elif block.get('type') == 'tool_result':
                    parts.append(toolResultSearchText(msg.get('toolUseResult')))
            raw = '\n'.join(part for part in parts if part)
    elif msg_type == 'assistant':
        content = (msg.get('message') or {}).get('content')
        if isinstance(content, list):
            parts: list[str] = []
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get('type') == 'text' and isinstance(block.get('text'), str):
                    parts.append(block['text'])
                elif block.get('type') == 'tool_use':
                    parts.append(toolUseSearchText(block.get('input')))
            raw = '\n'.join(part for part in parts if part)
    elif msg_type == 'attachment':
        attachment = msg.get('attachment') or {}
        if attachment.get('type') == 'relevant_memories':
            raw = '\n'.join(
                mem.get('content', '') for mem in attachment.get('memories', []) if isinstance(mem, dict)
            )
        elif (
            attachment.get('type') == 'queued_command'
            and attachment.get('commandMode') != 'task-notification'
            and not attachment.get('isMeta')
        ):
            prompt = attachment.get('prompt')
            if isinstance(prompt, str):
                raw = prompt
            elif isinstance(prompt, list):
                raw = '\n'.join(
                    block.get('text', '') for block in prompt if isinstance(block, dict) and block.get('type') == 'text'
                )
    elif msg_type == 'collapsed_read_search':
        memories = msg.get('relevantMemories') or []
        raw = '\n'.join(mem.get('content', '') for mem in memories if isinstance(mem, dict))

    return _strip_system_reminders(raw)


def toolUseSearchText(input: Any) -> str:
    if not isinstance(input, dict):
        return ''
    parts: list[str] = []
    for key in ['command', 'pattern', 'file_path', 'path', 'prompt', 'description', 'query', 'url', 'skill']:
        value = input.get(key)
        if isinstance(value, str):
            parts.append(value)
    for key in ['args', 'files']:
        value = input.get(key)
        if isinstance(value, list) and all(isinstance(item, str) for item in value):
            parts.append(' '.join(value))
    return '\n'.join(parts)


def toolResultSearchText(r: Any) -> str:
    if isinstance(r, str):
        return r
    if not isinstance(r, dict):
        return ''
    if isinstance(r.get('stdout'), str):
        stderr = r.get('stderr') if isinstance(r.get('stderr'), str) else ''
        return r['stdout'] + (('\n' + stderr) if stderr else '')
    file_obj = r.get('file')
    if isinstance(file_obj, dict) and isinstance(file_obj.get('content'), str):
        return file_obj['content']
    parts: list[str] = []
    for key in ['content', 'output', 'result', 'text', 'message']:
        value = r.get(key)
        if isinstance(value, str):
            parts.append(value)
    for key in ['filenames', 'lines', 'results']:
        value = r.get(key)
        if isinstance(value, list) and all(isinstance(item, str) for item in value):
            parts.append('\n'.join(value))
    return '\n'.join(parts)


renderable_search_text = renderableSearchText
compute_search_text = computeSearchText
tool_use_search_text = toolUseSearchText
tool_result_search_text = toolResultSearchText

