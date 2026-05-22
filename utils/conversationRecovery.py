"""
Port of src/utils/conversationRecovery.ts
"""
from __future__ import annotations

from typing import Any, Dict
import json
from datetime import datetime

from ..bootstrap.state import addInvokedSkill
from .cwd import get_cwd
from .listSessionsImpl import listSessionsImpl
from .messages import createUserMessage
from .sessionStorage import buildAttributionSnapshotChain, buildConversationChain, buildFileHistorySnapshotChain, findLatestMessage, loadTranscriptFile, removeExtraFields
from .sessionStoragePortable import resolveSessionFilePath


TeleportRemoteResponse = Dict[str, Any]
TurnInterruptionState = Any
DeserializeResult = Dict[str, Any]
InternalInterruptionState = Any
NO_RESPONSE_REQUESTED = "No response requested."


def migrateLegacyAttachmentTypes(message):
    """Transforms legacy attachment types to current types for backward compatibility"""
    if not isinstance(message, dict):
        return message
    if message.get('type') != 'attachment':
        return message

    attachment = message.get('attachment')
    if not isinstance(attachment, dict):
        return message

    if attachment.get('type') == 'new_file':
        updated_attachment = dict(attachment)
        updated_attachment['type'] = 'file'
        if 'displayPath' not in updated_attachment:
            updated_attachment['displayPath'] = attachment.get('filename')
        updated_message = dict(message)
        updated_message['attachment'] = updated_attachment
        return updated_message

    if attachment.get('type') == 'new_directory':
        updated_attachment = dict(attachment)
        updated_attachment['type'] = 'directory'
        if 'displayPath' not in updated_attachment:
            updated_attachment['displayPath'] = attachment.get('path')
        updated_message = dict(message)
        updated_message['attachment'] = updated_attachment
        return updated_message

    if 'displayPath' not in attachment:
        raw_path = attachment.get('filename') or attachment.get('path') or attachment.get('skillDir')
        if raw_path:
            updated_attachment = dict(attachment)
            updated_attachment['displayPath'] = raw_path
            updated_message = dict(message)
            updated_message['attachment'] = updated_attachment
            return updated_message

    return message


def _message_type(message):
    if not isinstance(message, dict):
        return None
    return message.get('type') or message.get('role')


def _message_content(message):
    if not isinstance(message, dict):
        return None
    nested = message.get('message')
    if isinstance(nested, dict):
        return nested.get('content')
    return message.get('content')


def _is_tool_result_message(message):
    content = _message_content(message)
    return isinstance(content, list) and len(content) == 1 and isinstance(content[0], dict) and content[0].get('type') == 'tool_result'


def _is_api_error_assistant(message):
    return _message_type(message) == 'assistant' and bool(isinstance(message, dict) and message.get('isApiErrorMessage'))


def _filter_whitespace_only_assistant_messages(messages):
    filtered = []
    for message in messages:
        if _message_type(message) != 'assistant':
            filtered.append(message)
            continue
        content = _message_content(message)
        if isinstance(content, str) and not content.strip():
            continue
        if isinstance(content, list):
            text_blocks = [block.get('text', '') for block in content if isinstance(block, dict) and block.get('type') == 'text']
            if text_blocks and not ''.join(str(block) for block in text_blocks).strip():
                continue
        filtered.append(message)
    return filtered


def _create_assistant_sentinel():
    return {
        'role': 'assistant',
        'type': 'assistant',
        'message': {'role': 'assistant', 'content': NO_RESPONSE_REQUESTED},
        'content': NO_RESPONSE_REQUESTED,
        'isMeta': True,
    }


def deserializeMessages(serializedMessages):
    """Deserializes messages from a log file into the format expected by the REPL.
Filters unresolved tool uses, orphaned thinking messages, and appends a
synthetic assistant sentinel when the last message is from the user.
@internal Exported for testing - use loadConversationForResume instead"""
    return deserializeMessagesWithInterruptDetection(serializedMessages).get('messages', [])


def deserializeMessagesWithInterruptDetection(serializedMessages):
    """Like deserializeMessages, but also detects whether the session was
interrupted mid-turn. Used by the SDK resume path to auto-continue
interrupted turns after a gateway-triggered restart.
@internal Exported for testing"""
    if not isinstance(serializedMessages, list):
        return {'messages': [], 'turnInterruptionState': {'kind': 'none'}}

    migrated = [migrateLegacyAttachmentTypes(message) for message in serializedMessages if isinstance(message, dict)]

    valid_modes = {'default', 'acceptEdits', 'bypassPermissions', 'plan'}
    for message in migrated:
        if _message_type(message) == 'user' and message.get('permissionMode') not in valid_modes:
            if 'permissionMode' in message:
                message['permissionMode'] = None

    filtered_messages = _filter_whitespace_only_assistant_messages(migrated)
    interruption_state = detectTurnInterruption(filtered_messages)

    if interruption_state.get('kind') == 'interrupted_turn':
        continuation_message = createUserMessage({'content': 'Continue from where you left off.'})
        continuation_message['isMeta'] = True
        filtered_messages.append(continuation_message)
        interruption_state = {'kind': 'interrupted_prompt', 'message': continuation_message}

    last_relevant_idx = -1
    for index in range(len(filtered_messages) - 1, -1, -1):
        message_type = _message_type(filtered_messages[index])
        if message_type not in {'system', 'progress'}:
            last_relevant_idx = index
            break

    if last_relevant_idx != -1 and _message_type(filtered_messages[last_relevant_idx]) == 'user':
        filtered_messages.insert(last_relevant_idx + 1, _create_assistant_sentinel())

    return {'messages': filtered_messages, 'turnInterruptionState': interruption_state}


def detectTurnInterruption(messages):
    """Determines whether the conversation was interrupted mid-turn based on the
last message after filtering. An assistant as last message (after filtering
unresolved tool_uses) is treated as a completed turn because stop_reason is
always null on persisted messages in the streaming path.

System and progress messages are skipped when finding the last turn-relevant
message — they are bookkeeping artifacts that should not mask a genuine
interruption. Attachments are kept as part of the turn."""
    if not isinstance(messages, list) or not messages:
        return {'kind': 'none'}

    last_message = None
    last_message_idx = -1
    for index in range(len(messages) - 1, -1, -1):
        candidate = messages[index]
        candidate_type = _message_type(candidate)
        if candidate_type in {'system', 'progress'}:
            continue
        if _is_api_error_assistant(candidate):
            continue
        last_message = candidate
        last_message_idx = index
        break

    if last_message is None:
        return {'kind': 'none'}

    last_type = _message_type(last_message)
    if last_type == 'assistant':
        return {'kind': 'none'}

    if last_type == 'user':
        if last_message.get('isMeta') or last_message.get('isCompactSummary'):
            return {'kind': 'none'}
        if _is_tool_result_message(last_message):
            if isTerminalToolResult(last_message, messages, last_message_idx):
                return {'kind': 'none'}
            return {'kind': 'interrupted_turn'}
        return {'kind': 'interrupted_prompt', 'message': last_message}

    if last_type == 'attachment':
        return {'kind': 'interrupted_turn'}

    return {'kind': 'none'}


def isTerminalToolResult(result, messages, resultIdx):
    """Is this tool_result the output of a tool that legitimately terminates a
turn? SendUserMessage is the canonical case: in brief mode, calling it is
the turn's final act — there is no follow-up assistant text (#20467
removed it). A transcript ending here means the turn COMPLETED, not that
it was killed mid-tool.

Walks back to find the assistant tool_use that this result belongs to and
checks its name. The matching tool_use is typically the immediately
preceding relevant message (filterUnresolvedToolUses has already dropped
unpaired ones), but we walk just in case system/progress noise is
interleaved."""
    content = _message_content(result)
    if not (isinstance(content, list) and content and isinstance(content[0], dict)):
        return False
    tool_block = content[0]
    if tool_block.get('type') != 'tool_result':
        return False
    tool_use_id = tool_block.get('tool_use_id')
    if not tool_use_id:
        return False

    terminal_names = {'SendUserMessage', 'Brief', 'LegacyBrief', 'SendUserFile'}
    for index in range(resultIdx - 1, -1, -1):
        message = messages[index]
        if _message_type(message) != 'assistant':
            continue
        content_blocks = _message_content(message)
        if not isinstance(content_blocks, list):
            continue
        for block in content_blocks:
            if isinstance(block, dict) and block.get('type') == 'tool_use' and block.get('id') == tool_use_id:
                return block.get('name') in terminal_names
    return False


def restoreSkillStateFromMessages(messages):
    """Restores skill state from invoked_skills attachments in messages.
This ensures that skills are preserved across resume after compaction.
Without this, if another compaction happens after resume, the skills would be lost
because STATE.invokedSkills would be empty.
@internal Exported for testing - use loadConversationForResume instead"""
    if not isinstance(messages, list):
        return None
    for message in messages:
        if _message_type(message) != 'attachment':
            continue
        attachment = message.get('attachment')
        if not isinstance(attachment, dict):
            continue
        if attachment.get('type') != 'invoked_skills':
            continue
        for skill in attachment.get('skills', []) or []:
            if not isinstance(skill, dict):
                continue
            if skill.get('name') and skill.get('path') and skill.get('content'):
                addInvokedSkill(skill['name'], skill['path'], skill['content'], None)
    return None


async def loadMessagesFromJsonlPath(path):
    """Chain-walk a transcript jsonl by path.  Same sequence loadFullLog
runs internally — loadTranscriptFile → find newest non-sidechain
leaf → buildConversationChain → removeExtraFields — just starting
from an arbitrary path instead of the sid-derived one.

leafUuids is populated by loadTranscriptFile as "uuids that no
other message's parentUuid points at" — the chain tips.  There can
be several (sidechains, orphans); newest non-sidechain is the main
conversation's end."""
    try:
        loaded = await loadTranscriptFile(path)
        messages = loaded.get('messages', {})
        leaf_uuids = loaded.get('leafUuids', set())
        if not messages:
            return {'messages': [], 'sessionId': None}

        tip = findLatestMessage(
            messages.values(),
            lambda message: message.get('uuid') in leaf_uuids and not message.get('isSidechain'),
        )
        if not tip:
            return {'messages': [], 'sessionId': None}

        chain = buildConversationChain(messages, tip)
        session_id = tip.get('sessionId')
        if not session_id:
            for message in reversed(chain):
                if isinstance(message, dict) and message.get('sessionId'):
                    session_id = message.get('sessionId')
                    break
        return {
            'messages': removeExtraFields(chain),
            'sessionId': session_id,
            'fullPath': path,
            'summary': loaded.get('summaries', {}).get(tip.get('uuid')),
            'customTitle': loaded.get('customTitles', {}).get(session_id),
            'tag': loaded.get('tags', {}).get(session_id),
            'agentName': loaded.get('agentNames', {}).get(session_id),
            'agentColor': loaded.get('agentColors', {}).get(session_id),
            'agentSetting': loaded.get('agentSettings', {}).get(session_id),
            'mode': loaded.get('modes', {}).get(session_id),
            'prNumber': loaded.get('prNumbers', {}).get(session_id),
            'prUrl': loaded.get('prUrls', {}).get(session_id),
            'prRepository': loaded.get('prRepositories', {}).get(session_id),
            'worktreeSession': loaded.get('worktreeStates', {}).get(session_id),
            'fileHistorySnapshots': buildFileHistorySnapshotChain(loaded.get('fileHistorySnapshots'), chain),
            'attributionSnapshots': buildAttributionSnapshotChain(loaded.get('attributionSnapshots'), chain),
            'contentReplacements': loaded.get('contentReplacements', {}).get(session_id) or [],
            'contextCollapseCommits': [
                entry for entry in (loaded.get('contextCollapseCommits') or [])
                if isinstance(entry, dict) and entry.get('sessionId') == session_id
            ],
            'contextCollapseSnapshot': (
                loaded.get('contextCollapseSnapshot')
                if isinstance(loaded.get('contextCollapseSnapshot'), dict)
                and loaded.get('contextCollapseSnapshot', {}).get('sessionId') == session_id
                else None
            ),
        }
    except Exception:
        return {'messages': [], 'sessionId': None}


async def loadConversationForResume(source, sourceJsonlFile):
    """Loads a conversation for resume from various sources.
This is the centralized function for loading and deserializing conversations.

@param source - The source to load from:
- undefined: load most recent conversation
- string: session ID to load
- LogOption: already loaded conversation
@param sourceJsonlFile - Alternate: path to a transcript jsonl.
Used when --resume receives a .jsonl path (cli/print.ts routes
on suffix), typically for cross-directory resume where the
transcript lives outside the current project dir.
@returns Object containing the deserialized messages and the original log, or null if not found"""
    messages = []
    session_id = None
    metadata = {}

    if sourceJsonlFile:
        loaded = await loadMessagesFromJsonlPath(sourceJsonlFile)
        messages = loaded.get('messages', [])
        session_id = loaded.get('sessionId')
        metadata = loaded
    elif source is None:
        recent_sessions = await listSessionsImpl({
            'dir': get_cwd(),
            'limit': 1,
            'includeWorktrees': True,
        })
        if recent_sessions:
            recent_session_id = recent_sessions[0].get('sessionId')
            if recent_session_id:
                resolved = await resolveSessionFilePath(recent_session_id, get_cwd())
                if resolved:
                    loaded = await loadMessagesFromJsonlPath(resolved['filePath'])
                    messages = loaded.get('messages', [])
                    session_id = loaded.get('sessionId') or recent_session_id
                    metadata = loaded
    elif isinstance(source, str) and source.endswith('.jsonl'):
        loaded = await loadMessagesFromJsonlPath(source)
        messages = loaded.get('messages', [])
        session_id = loaded.get('sessionId')
        metadata = loaded
    elif isinstance(source, str):
        resolved = await resolveSessionFilePath(source)
        if resolved:
            loaded = await loadMessagesFromJsonlPath(resolved['filePath'])
            messages = loaded.get('messages', [])
            session_id = loaded.get('sessionId') or source
            metadata = loaded
    elif isinstance(source, dict) and isinstance(source.get('messages'), list):
        messages = source.get('messages', [])
        session_id = source.get('sessionId')
        metadata = source
    elif isinstance(source, list):
        messages = source

    if not messages:
        return None

    deserialized = deserializeMessagesWithInterruptDetection(messages)
    restoreSkillStateFromMessages(deserialized.get('messages', []))
    return {
        'messages': deserialized.get('messages', []),
        'turnInterruptionState': deserialized.get('turnInterruptionState', {'kind': 'none'}),
        'sessionId': session_id,
        'fullPath': metadata.get('fullPath') or sourceJsonlFile or (source if isinstance(source, str) and source.endswith('.jsonl') else None),
        'summary': metadata.get('summary'),
        'customTitle': metadata.get('customTitle'),
        'tag': metadata.get('tag'),
        'agentName': metadata.get('agentName'),
        'agentColor': metadata.get('agentColor'),
        'agentSetting': metadata.get('agentSetting'),
        'mode': metadata.get('mode'),
        'prNumber': metadata.get('prNumber'),
        'prUrl': metadata.get('prUrl'),
        'prRepository': metadata.get('prRepository'),
        'worktreeSession': metadata.get('worktreeSession'),
        'fileHistorySnapshots': metadata.get('fileHistorySnapshots') or [],
        'attributionSnapshots': metadata.get('attributionSnapshots') or [],
        'contentReplacements': metadata.get('contentReplacements'),
        'contextCollapseCommits': metadata.get('contextCollapseCommits'),
        'contextCollapseSnapshot': metadata.get('contextCollapseSnapshot'),
    }

