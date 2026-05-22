"""
    passpasspasspasspasspasspasspassPortpasssrc/utils/sessionStorage
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
import os
import os.path
import subprocess
import json
import re
import asyncio
import hashlib
import uuid
import time
from datetime import datetime, timezone, timedelta
import glob
import platform
import logging
import math
import random
from enum import Enum, auto
from collections import defaultdict
from functools import lru_cache, wraps
import ssl
import socket
import struct

from ..bootstrap.state import getOriginalCwd, getSessionId, getSessionProjectDir
from .envUtils import get_vivian_config_home_dir


join = os.path.join
unlink = os.unlink


def sanitizePath(path: str) -> str:
    sanitized = os.path.realpath(path)
    return sanitized.replace(os.sep, "-").lstrip("-")


class _SimpleMap(dict):
    def set(self, key, value):
        self[key] = value

    def delete(self, key):
        self.pop(key, None)


agentTranscriptSubdirs = _SimpleMap()


def isFsInaccessible(_error) -> bool:
    return False


class _LocalFsImplementation:
    def statSync(self, path: str):
        return os.stat(path)


def getFsImplementation():
    return _LocalFsImplementation()


Transcript = Any
LegacyProgressEntry = Dict[str, Any]
AgentMetadata = Dict[str, Any]
RemoteAgentMetadata = Dict[str, Any]
InternalEventWriter = Any
InternalEventReader = Any


class Project:
    def __init__(self):
        self.sessionFile: str | None = None
        self.pendingEntries: list[Any] = []
        self.remote_ingress_url: str | None = None
        self.internal_event_writer: InternalEventWriter | None = None
        self.internal_event_reader: InternalEventReader | None = None
        self.internal_subagent_event_reader: InternalEventReader | None = None
        self.pendingWriteCount: int = 0
        self.flushResolvers: list[Callable[[], None]] = []
        self.writeQueues: dict[str, list[Any]] = {}
        self.flushTimer: Any = None
        self.activeDrain: Any = None

    def _resetFlushState(self) -> None:
        self.pendingWriteCount = 0
        self.flushResolvers = []
        self.writeQueues = {}
        self.flushTimer = None
        self.activeDrain = None

    def set_internal_event_writer(self, writer: InternalEventWriter) -> None:
        self.internal_event_writer = writer

    def set_internal_event_reader(self, reader: InternalEventReader) -> None:
        self.internal_event_reader = reader

    def set_internal_subagent_event_reader(self, reader: InternalEventReader) -> None:
        self.internal_subagent_event_reader = reader

    def set_remote_ingress_url(self, url: str | None) -> None:
        self.remote_ingress_url = url

    def resetSessionFile(self) -> None:
        self.sessionFile = None
        self.pendingEntries = []



MAX_TRANSCRIPT_READ_BYTES: Any = None  # type: ignore
_project_singleton: Project | None = None


def getProjectDir(projectDir):
    return os.path.join(getProjectsDir(), sanitizePath(projectDir))


def isTranscriptMessage(entry):
    """Type guard to check if an entry is a transcript message."""
    return isinstance(entry, dict) and entry.get('type') in {'user', 'assistant', 'attachment', 'system'}


def isChainParticipant(m):
    """Entries that participate in the parentUuid chain. Used on the write path"""
    return not (isinstance(m, dict) and m.get('type') == 'progress')


def isLegacyProgressEntry(entry):
    """Progress entries in transcripts written before PR #24099. They are not"""
    return (
        isinstance(entry, dict)
        and entry.get('type') == 'progress'
        and isinstance(entry.get('uuid'), str)
    )


def isEphemeralToolProgress(dataType):
    return isinstance(dataType, str) and dataType in {
        'bash_progress',
        'edit_progress',
        'replace_progress',
        'write_progress',
        'notebook_edit_progress',
        'multiedit_progress',
        'glob_progress',
        'grep_progress',
        'task_status',
        'webfetch_progress',
        'websearch_progress',
        'agent_progress',
        'thinking',
        'powershell_progress',
        'mcp_progress',
        'sleep_progress',
    }


def getProjectsDir():
    return os.path.join(get_vivian_config_home_dir(), 'projects')


def getTranscriptPath():
    projectDir = getSessionProjectDir() if getSessionProjectDir() is not None else getProjectDir(getOriginalCwd())
    return os.path.join(projectDir, f"{getSessionId()}.jsonl")


def getTranscriptPathForSession(sessionId):
        # When asking for the CURRENT session's transcript, honor sessionProjectDir
    # the same way getTranscriptPath() does. Without this, hooks get a
    # transcript_path computed from originalCwd while the actual file was
    # written to sessionProjectDir (set by switchActiveSession on resume/branch)
    # — different directories, so the hook sees MISSING (gh-30217). CC-34
    # made sessionId + sessionProjectDir atomic precisely to prevent this
    # kind of drift; this function just wasn't updated to read both.
    # 
    # For OTHER session IDs we can only guess via originalCwd — we don't
    # track a sessionId→projectDir map. Callers wanting a specific other
    # session's path should pass fullPath explicitly (most save* functions
    # already accept this).
    if sessionId == getSessionId():
        return getTranscriptPath()
    projectDir = getProjectDir(getOriginalCwd())
    return os.path.join(projectDir, f"{sessionId}.jsonl")


def setAgentTranscriptSubdir(agentId, subdir):
    agentTranscriptSubdirs.set(agentId, subdir)


def clearAgentTranscriptSubdir(agentId):
    agentTranscriptSubdirs.delete(agentId)


def getAgentTranscriptPath(agentId):
    projectDir = getSessionProjectDir() if getSessionProjectDir() is not None else getProjectDir(getOriginalCwd())
    sessionId = getSessionId()
    subdir = agentTranscriptSubdirs.get(agentId)
    base = join(projectDir, sessionId, 'subagents', subdir) if subdir else join(projectDir, sessionId, 'subagents')
    return join(base, f"agent-{agentId}.jsonl")


def getAgentMetadataPath(agentId):
    transcript_path = getAgentTranscriptPath(agentId)
    if transcript_path.endswith('.jsonl'):
        return transcript_path[:-6] + '.meta.json'
    return transcript_path + '.meta.json'


async def writeAgentMetadata(agentId, metadata):
    """Persist the agentType used to launch a subagent. Read by resume to"""
    path = getAgentMetadataPath(agentId)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(metadata, handle)
    return None


async def readAgentMetadata(agentId):
    path = getAgentMetadataPath(agentId)
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            return json.load(handle)
    except Exception as e:
        if isFsInaccessible(e):
            return None
        raise e


def getRemoteAgentsDir():
    # Same sessionProjectDir fallback as getAgentTranscriptPath — the project
    # dir (containing the .jsonl), not the session dir, so sessionId is joined.
    projectDir = getSessionProjectDir() if getSessionProjectDir() is not None else getProjectDir(getOriginalCwd())
    return join(projectDir, getSessionId(), 'remote-agents')


def getRemoteAgentMetadataPath(taskId):
        return join(getRemoteAgentsDir(), f"remote-agent-{taskId}.meta.json")


async def writeRemoteAgentMetadata(taskId, metadata):
    """Persist metadata for a remote-agent task so it can be restored on session"""
    path = getRemoteAgentMetadataPath(taskId)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(metadata, handle)
    return None


async def readRemoteAgentMetadata(taskId):
    path = getRemoteAgentMetadataPath(taskId)
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            return json.load(handle)
    except Exception as e:
        if isFsInaccessible(e):
            return None
        raise e


async def deleteRemoteAgentMetadata(taskId):
    path = getRemoteAgentMetadataPath(taskId)
    try:
        unlink(path)
    except Exception as e:
        if isFsInaccessible(e):
            return
        raise e


async def listRemoteAgentMetadata():
    """Scan the remote-agents/ directory for all persisted metadata files."""
    directory = getRemoteAgentsDir()
    try:
        entries = list(os.scandir(directory))
    except Exception as e:
        if isFsInaccessible(e):
            return []
        raise e

    results = []
    for entry in entries:
        if not entry.is_file() or not entry.name.endswith('.meta.json'):
            continue
        try:
            with open(entry.path, 'r', encoding='utf-8') as handle:
                results.append(json.load(handle))
        except Exception:
            continue
    return results


def sessionIdExists(sessionId):
    projectDir = getProjectDir(getOriginalCwd())
    sessionFile = join(projectDir, f"{sessionId}.jsonl")
    fs = getFsImplementation()
    try:
        fs.statSync(sessionFile)
        return True
    except Exception:
        return False


def getNodeEnv():
    return os.environ.get("NODE_ENV", "") or 'development'


def getUserType():
    return os.environ.get("USER_TYPE", "") or 'external'


def getEntrypoint():
    return os.environ.get("vivian_CODE_ENTRYPOINT", "")


def isCustomTitleEnabled():
    return True


def _parse_timestamp_ms(timestamp):
    if not isinstance(timestamp, str):
        return 0
    try:
        return int(datetime.fromisoformat(timestamp.replace('Z', '+00:00')).timestamp() * 1000)
    except Exception:
        return 0


async def loadTranscriptFile(sessionFile):
    messages = {}
    leaf_uuids = set()
    parent_uuids = set()
    summaries = {}
    custom_titles = {}
    tags = {}
    agent_names = {}
    agent_colors = {}
    agent_settings = {}
    modes = {}
    pr_numbers = {}
    pr_urls = {}
    pr_repositories = {}
    worktree_states = {}
    file_history_snapshots = {}
    attribution_snapshots = {}
    content_replacements = {}
    context_collapse_commits = []
    context_collapse_snapshot = None

    try:
        with open(sessionFile, 'r', encoding='utf-8') as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except Exception:
                    continue
                if not isinstance(entry, dict):
                    continue
                entry_type = entry.get('type')
                session_id = entry.get('sessionId')
                if entry_type == 'summary' and isinstance(entry.get('leafUuid'), str):
                    summaries[entry['leafUuid']] = entry.get('summary')
                    continue
                if isinstance(session_id, str):
                    if entry_type == 'custom-title' and isinstance(entry.get('customTitle'), str):
                        custom_titles[session_id] = entry['customTitle']
                        continue
                    if entry_type == 'tag' and isinstance(entry.get('tag'), str):
                        tags[session_id] = entry['tag']
                        continue
                    if entry_type == 'agent-name' and isinstance(entry.get('agentName'), str):
                        agent_names[session_id] = entry['agentName']
                        continue
                    if entry_type == 'agent-color' and isinstance(entry.get('agentColor'), str):
                        agent_colors[session_id] = entry['agentColor']
                        continue
                    if entry_type == 'agent-setting' and isinstance(entry.get('agentSetting'), str):
                        agent_settings[session_id] = entry['agentSetting']
                        continue
                    if entry_type == 'mode' and isinstance(entry.get('mode'), str):
                        modes[session_id] = entry['mode']
                        continue
                    if entry_type == 'pr-link':
                        if isinstance(entry.get('prNumber'), int):
                            pr_numbers[session_id] = entry['prNumber']
                        if isinstance(entry.get('prUrl'), str):
                            pr_urls[session_id] = entry['prUrl']
                        if isinstance(entry.get('prRepository'), str):
                            pr_repositories[session_id] = entry['prRepository']
                        continue
                    if entry_type == 'worktree-state':
                        worktree_states[session_id] = entry.get('worktreeSession')
                        continue
                    if entry_type == 'content-replacement' and isinstance(entry.get('replacements'), list):
                        existing = content_replacements.get(session_id)
                        if existing is None:
                            existing = []
                            content_replacements[session_id] = existing
                        existing.extend(entry['replacements'])
                        continue
                if entry_type == 'file-history-snapshot' and isinstance(entry.get('messageId'), str):
                    file_history_snapshots[entry['messageId']] = entry
                    continue
                if entry_type == 'attribution-snapshot' and isinstance(entry.get('messageId'), str):
                    attribution_snapshots[entry['messageId']] = entry
                    continue
                if entry_type == 'marble-origami-commit':
                    context_collapse_commits.append(entry)
                    continue
                if entry_type == 'marble-origami-snapshot':
                    context_collapse_snapshot = entry
                    continue
                if not isTranscriptMessage(entry):
                    continue
                uuid = entry.get('uuid')
                if not isinstance(uuid, str):
                    continue
                messages[uuid] = entry
                parent_uuid = entry.get('parentUuid')
                if isinstance(parent_uuid, str):
                    parent_uuids.add(parent_uuid)
        leaf_uuids = set(messages.keys()) - parent_uuids
    except Exception:
        messages = {}
        leaf_uuids = set()
        summaries = {}
        custom_titles = {}
        tags = {}
        agent_names = {}
        agent_colors = {}
        agent_settings = {}
        modes = {}
        pr_numbers = {}
        pr_urls = {}
        pr_repositories = {}
        worktree_states = {}
        file_history_snapshots = {}
        attribution_snapshots = {}
        content_replacements = {}
        context_collapse_commits = []
        context_collapse_snapshot = None

    return {
        'messages': messages,
        'leafUuids': leaf_uuids,
        'summaries': summaries,
        'customTitles': custom_titles,
        'tags': tags,
        'agentNames': agent_names,
        'agentColors': agent_colors,
        'agentSettings': agent_settings,
        'modes': modes,
        'prNumbers': pr_numbers,
        'prUrls': pr_urls,
        'prRepositories': pr_repositories,
        'worktreeStates': worktree_states,
        'fileHistorySnapshots': file_history_snapshots,
        'attributionSnapshots': attribution_snapshots,
        'contentReplacements': content_replacements,
        'contextCollapseCommits': context_collapse_commits,
        'contextCollapseSnapshot': context_collapse_snapshot,
    }


def findLatestMessage(messages, predicate=None):
    latest = None
    latest_ts = -1
    for message in messages:
        if predicate and not predicate(message):
            continue
        timestamp_ms = _parse_timestamp_ms(message.get('timestamp'))
        if timestamp_ms >= latest_ts:
            latest = message
            latest_ts = timestamp_ms
    return latest


def buildConversationChain(messages, leafMessage):
    transcript = []
    seen = set()
    current = leafMessage
    while isinstance(current, dict):
        current_uuid = current.get('uuid')
        if isinstance(current_uuid, str):
            if current_uuid in seen:
                break
            seen.add(current_uuid)
        transcript.append(current)
        parent_uuid = current.get('parentUuid')
        current = messages.get(parent_uuid) if isinstance(parent_uuid, str) else None
    transcript.reverse()
    return recoverOrphanedParallelToolResults(messages, transcript, seen)


def buildFileHistorySnapshotChain(fileHistorySnapshots, conversation):
    snapshots = []
    index_by_message_id = {}
    for message in conversation:
        if not isinstance(message, dict):
            continue
        message_uuid = message.get('uuid')
        if not isinstance(message_uuid, str):
            continue
        snapshot_message = (fileHistorySnapshots or {}).get(message_uuid)
        if not isinstance(snapshot_message, dict):
            continue
        snapshot = snapshot_message.get('snapshot')
        if not isinstance(snapshot, dict):
            continue
        snapshot_message_id = snapshot.get('messageId')
        if not isinstance(snapshot_message_id, str):
            continue
        existing_index = index_by_message_id.get(snapshot_message_id) if snapshot_message.get('isSnapshotUpdate') else None
        if existing_index is None:
            index_by_message_id[snapshot_message_id] = len(snapshots)
            snapshots.append(snapshot)
        else:
            snapshots[existing_index] = snapshot
    return snapshots


def buildAttributionSnapshotChain(attributionSnapshots, _conversation):
    return [snapshot for snapshot in (attributionSnapshots or {}).values() if isinstance(snapshot, dict)]


def recoverOrphanedParallelToolResults(messages, chain, seen):
    chain_assistants = [
        message for message in chain
        if isinstance(message, dict) and message.get('type') == 'assistant'
    ]
    if not chain_assistants:
        return chain

    anchor_by_msg_id = {}
    for assistant in chain_assistants:
        message_payload = assistant.get('message')
        if isinstance(message_payload, dict) and isinstance(message_payload.get('id'), str):
            anchor_by_msg_id[message_payload['id']] = assistant

    siblings_by_msg_id = {}
    tool_results_by_asst = {}
    for message in messages.values():
        if not isinstance(message, dict):
            continue
        if message.get('type') == 'assistant':
            message_payload = message.get('message')
            if isinstance(message_payload, dict) and isinstance(message_payload.get('id'), str):
                siblings_by_msg_id.setdefault(message_payload['id'], []).append(message)
            continue
        if message.get('type') != 'user':
            continue
        parent_uuid = message.get('parentUuid')
        content = message.get('message', {}).get('content') if isinstance(message.get('message'), dict) else None
        if not isinstance(parent_uuid, str) or not isinstance(content, list):
            continue
        if not any(isinstance(block, dict) and block.get('type') == 'tool_result' for block in content):
            continue
        tool_results_by_asst.setdefault(parent_uuid, []).append(message)

    processed_groups = set()
    inserts = {}
    for assistant in chain_assistants:
        message_payload = assistant.get('message')
        msg_id = message_payload.get('id') if isinstance(message_payload, dict) else None
        if not isinstance(msg_id, str) or msg_id in processed_groups:
            continue
        processed_groups.add(msg_id)

        group = siblings_by_msg_id.get(msg_id, [assistant])
        orphaned_siblings = [member for member in group if member.get('uuid') not in seen]
        orphaned_tool_results = []
        for member in group:
            for tool_result in tool_results_by_asst.get(member.get('uuid'), []):
                if tool_result.get('uuid') not in seen:
                    orphaned_tool_results.append(tool_result)

        if not orphaned_siblings and not orphaned_tool_results:
            continue

        orphaned_siblings.sort(key=lambda message: str(message.get('timestamp') or ''))
        orphaned_tool_results.sort(key=lambda message: str(message.get('timestamp') or ''))

        recovered = [*orphaned_siblings, *orphaned_tool_results]
        for recovered_message in recovered:
            recovered_uuid = recovered_message.get('uuid')
            if isinstance(recovered_uuid, str):
                seen.add(recovered_uuid)

        anchor = anchor_by_msg_id.get(msg_id)
        if anchor and isinstance(anchor.get('uuid'), str):
            inserts[anchor['uuid']] = recovered

    if not inserts:
        return chain

    result = []
    for message in chain:
        result.append(message)
        message_uuid = message.get('uuid') if isinstance(message, dict) else None
        if isinstance(message_uuid, str) and message_uuid in inserts:
            result.extend(inserts[message_uuid])
    return result


def removeExtraFields(transcript):
    if not isinstance(transcript, list):
        return []
    return [message for message in transcript if isinstance(message, dict)]


def getProject():
    global _project_singleton
    if _project_singleton is None:
        _project_singleton = Project()
    return _project_singleton


def resetProjectFlushStateForTesting():
    """Reset the Project singleton's flush state for testing."""
    project = getProject()
    project._resetFlushState()
    return None


def resetProjectForTesting():
    """Reset the entire Project singleton for testing."""
    global _project_singleton
    _project_singleton = None
    return None


def setSessionFileForTesting(path):
    getProject().sessionFile = path


def _getActiveSessionFile(fullPath=None):
    if fullPath:
        return fullPath
    project = getProject()
    if project.sessionFile:
        return project.sessionFile
    return getTranscriptPath()


def appendSessionEntry(entry, fullPath=None):
    session_file = _getActiveSessionFile(fullPath)
    os.makedirs(os.path.dirname(session_file), exist_ok=True)
    with open(session_file, 'a', encoding='utf-8') as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + '\n')


def recordTranscript(messages, fullPath=None, startingParentUuid=None):
    parent_uuid = startingParentUuid
    session_id = getSessionId()
    recorded_parent_uuid = startingParentUuid
    timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    for message in messages:
        if not isinstance(message, dict):
            continue
        entry = {
            **message,
            'sessionId': session_id,
            'timestamp': message.get('timestamp') or timestamp,
        }
        if isChainParticipant(entry):
            entry['parentUuid'] = parent_uuid
        appendSessionEntry(entry, fullPath)
        if isChainParticipant(entry) and isinstance(entry.get('uuid'), str):
            parent_uuid = entry['uuid']
            recorded_parent_uuid = entry['uuid']
    return recorded_parent_uuid


def recordFileHistorySnapshot(messageId, snapshot, isSnapshotUpdate, fullPath=None):
    appendSessionEntry(
        {
            'type': 'file-history-snapshot',
            'messageId': messageId,
            'snapshot': snapshot,
            'isSnapshotUpdate': bool(isSnapshotUpdate),
        },
        fullPath,
    )


def recordAttributionSnapshot(snapshot, fullPath=None):
    appendSessionEntry(snapshot, fullPath)


def setInternalEventWriter(writer):
    """Register a CCR v2 internal event writer for transcript persistence."""
    getProject().set_internal_event_writer(writer)


def setInternalEventReader(reader, subagentReader):
    """Register a CCR v2 internal event reader for session resume."""
    getProject().set_internal_event_reader(reader)
    getProject().set_internal_subagent_event_reader(subagentReader)


def setRemoteIngressUrlForTesting(url):
    """Set the remote ingress URL on the current Project for testing."""
    getProject().set_remote_ingress_url(url)

