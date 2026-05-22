"""resume command — mirrors src/commands/resume/resume.tsx.

Resume a previous conversation session by ID or pick from recent sessions.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from ...types import Message
from ...bootstrap.state import switchSession
from ...utils.conversationRecovery import loadConversationForResume
from ...utils.listSessionsImpl import listSessionsImpl
from ...utils.sessionRestore import processResumedConversation

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


def _block_text(block: dict) -> str:
    if block.get('type') == 'text':
        return str(block.get('text') or '')
    if block.get('type') == 'tool_result':
        payload = block.get('content')
        if isinstance(payload, str):
            return payload
        return json.dumps(payload)
    return ''


def _message_content_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return ''.join(_block_text(block) for block in content if isinstance(block, dict))
    return ''


def _transcript_message_to_engine_message(message: dict) -> Message | None:
    if not isinstance(message, dict):
        return None
    message_type = message.get('type')
    payload = message.get('message') if isinstance(message.get('message'), dict) else {}
    content = payload.get('content') if isinstance(payload, dict) else message.get('content')

    if message_type == 'assistant':
        tool_calls = []
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get('type') == 'tool_use':
                    tool_calls.append({
                        'id': block.get('id'),
                        'type': 'function',
                        'function': {
                            'name': block.get('name'),
                            'arguments': json.dumps(block.get('input') or {}),
                        },
                    })
        return Message(
            role='assistant',
            content=_message_content_text(content) or None,
            tool_calls=tool_calls or None,
        )

    if message_type == 'user':
        if isinstance(content, list) and any(isinstance(block, dict) and block.get('type') == 'tool_result' for block in content):
            tool_result = next(block for block in content if isinstance(block, dict) and block.get('type') == 'tool_result')
            return Message(
                role='tool',
                content=_message_content_text(tool_result.get('content')) or None,
                tool_call_id=tool_result.get('tool_use_id'),
            )
        return Message(role='user', content=_message_content_text(content) or None)

    if message_type == 'system':
        return Message(role='system', content=_message_content_text(content) or message.get('content') or None)

    return None


def _to_engine_messages(messages: list[dict]) -> list[Message]:
    converted = []
    for message in messages:
        mapped = _transcript_message_to_engine_message(message)
        if mapped is not None:
            converted.append(mapped)
    return converted


def _last_transcript_uuid(messages: list[dict]) -> str | None:
    for message in reversed(messages):
        if isinstance(message, dict) and isinstance(message.get('uuid'), str):
            return str(message['uuid'])
    return None


async def call(args: str, context: CommandContext) -> TextResult:
    """Resume a session."""
    from ...types.command import TextResult

    session_id = args.strip() if args else None

    if session_id:
        result = await loadConversationForResume(session_id, None)
        if not result:
            return TextResult(value=f"Session not found: {session_id}")

        engine = getattr(context, 'engine', None)
        processed = await processResumedConversation(
            result,
            {
                'currentCwd': getattr(engine, 'cwd', None),
                'cliAgents': [],
                'initialState': engine.state_store.get_state() if engine is not None and hasattr(engine, 'state_store') else {},
                'agentDefinitions': (
                    engine.state_store.get_state().get('agentDefinitions')
                    if engine is not None and hasattr(engine, 'state_store')
                    else {}
                ),
                'mainThreadAgentDefinition': None,
            },
            {'forkSession': False, 'includeAttribution': True},
        )

        resumed_messages = _to_engine_messages(processed.get('messages') or result.get('messages') or [])
        if engine is not None:
            session_identifier = result.get('sessionId')
            full_path = result.get('fullPath')
            if session_identifier:
                switchSession(str(session_identifier), str(Path(full_path).parent) if full_path else None)
            engine.messages = resumed_messages
            if session_identifier:
                engine.session_id = str(session_identifier)
            setattr(engine, '_last_transcript_uuid', _last_transcript_uuid(processed.get('messages') or result.get('messages') or []))
            engine.turn_count = sum(1 for message in resumed_messages if getattr(message, 'role', None) == 'user')

            state_store = getattr(engine, 'state_store', None)
            if state_store is not None and hasattr(state_store, 'set_state'):
                state_store.set_state(lambda _prev: processed.get('initialState') or _prev)

        summary = result.get('summary') or result.get('customTitle') or ''
        summary_suffix = f" - {summary}" if summary else ''
        return TextResult(value=f"Resumed session {result.get('sessionId')}{summary_suffix} ({len(resumed_messages)} messages).")
    else:
        recent = await _list_recent_sessions(context)
        if recent:
            lines = ["Recent sessions:", ""]
            for i, s in enumerate(recent[:10], 1):
                session = str(s.get('sessionId', 'unknown'))
                preview = str(s.get('customTitle') or s.get('summary') or s.get('firstPrompt') or '')
                lines.append(f"  {i}. {session[:12]}... - {preview[:60]}")
            lines.append("")
            lines.append("Use /resume <id> to resume one.")
            return TextResult(value="\n".join(lines))
        return TextResult(value="No recent sessions found. Start a new conversation!")


async def _list_recent_sessions(context: CommandContext) -> list[dict]:
    """List recent sessions from transcript storage."""
    try:
        engine = getattr(context, 'engine', None)
        cwd = getattr(engine, 'cwd', None) or None
        return await listSessionsImpl({'dir': cwd, 'limit': 10, 'includeWorktrees': True})
    except Exception:
        return []


resumeSession = call
resume_session = call
