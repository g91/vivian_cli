"""
Port of src/utils/commitAttribution.ts
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
import os
import os.path
import json
import re
import asyncio
import hashlib
import subprocess
import uuid
import time
from datetime import datetime, timezone, timedelta
import math
import random
from collections import defaultdict
from contextvars import ContextVar
from functools import lru_cache, wraps

from ..bootstrap.state import getOriginalCwd, getSessionId


AttributionState = Dict[str, Any]
AttributionSummary = Dict[str, Any]
FileAttribution = Dict[str, Any]
AttributionData = Dict[str, Any]


# Check if the current repo is in the allowlist for internal model names.
isInternalModelRepo: Any = None  # type: ignore


def getAttributionRepoRoot():
    """Get the repo root for attribution operations."""
    return getOriginalCwd()


def getRepoClassCached():
    """Synchronously return the cached repo classification."""
    result = None
    _result: dict = {}
    # Implement getRepoClassCached
    return _result


def isInternalModelRepoCached():
    """Synchronously return the cached result of isInternalModelRepo()."""
    result = None
    _result: dict = {}
    # Implement isInternalModelRepoCached
    return _result


def sanitizeSurfaceKey(surfaceKey):
    """Sanitize a surface key to use public model names."""
    result = None
    _input = surfaceKey
    _output = _input if _input is not None else {}
    return _output


def sanitizeModelName(shortName):
    """Sanitize a model name to its public equivalent."""
    result = None
    _input = shortName
    _output = _input if _input is not None else {}
    return _output


def getClientSurface():
    """Get the current client surface from environment."""
    return os.environ.get('vivian_CODE_ENTRYPOINT', 'cli')


def buildSurfaceKey(surface, model):
    """Build a surface key that includes the model name."""
    result = None
    _input = surface
    _output = _input if _input is not None else {}
    return _output


def computeContentHash(content):
    """Compute SHA-256 hash of content."""
    payload = content if isinstance(content, str) else ''
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def normalizeFilePath(filePath):
    """Normalize file path to relative path from cwd for consistent tracking."""
    if not isinstance(filePath, str):
        return filePath
    if not os.path.isabs(filePath):
        return filePath.replace(os.sep, '/')
    cwd = getOriginalCwd()
    try:
        relative_path = os.path.relpath(os.path.realpath(filePath), os.path.realpath(cwd))
        if not relative_path.startswith('..' + os.sep) and relative_path != '..':
            return relative_path.replace(os.sep, '/')
    except Exception:
        pass
    return filePath.replace(os.sep, '/')


def expandFilePath(filePath):
    """Expand a relative path to absolute path."""
    if isinstance(filePath, str) and os.path.isabs(filePath):
        return filePath
    return os.path.join(getOriginalCwd(), str(filePath))


def createEmptyAttributionState():
    """Create an empty attribution state for a new session."""
    return {
        'fileStates': {},
        'sessionBaselines': {},
        'surface': getClientSurface(),
        'startingHeadSha': None,
        'promptCount': 0,
        'promptCountAtLastCommit': 0,
        'permissionPromptCount': 0,
        'permissionPromptCountAtLastCommit': 0,
        'escapeCount': 0,
        'escapeCountAtLastCommit': 0,
    }


def computeFileModificationState(existingFileStates, filePath, oldContent, newContent, mtime):
    """Compute the character contribution for a file modification."""
    normalized_path = normalizeFilePath(filePath)
    existing_state = existingFileStates.get(normalized_path) if isinstance(existingFileStates, dict) else None
    existing_contribution = int((existing_state or {}).get('vivianContribution') or 0)

    if oldContent == '' or newContent == '':
        vivian_contribution = len(newContent) if oldContent == '' else len(oldContent)
    else:
        min_len = min(len(oldContent), len(newContent))
        prefix_end = 0
        while prefix_end < min_len and oldContent[prefix_end] == newContent[prefix_end]:
            prefix_end += 1
        suffix_len = 0
        while (
            suffix_len < min_len - prefix_end
            and oldContent[len(oldContent) - 1 - suffix_len] == newContent[len(newContent) - 1 - suffix_len]
        ):
            suffix_len += 1
        old_changed_len = len(oldContent) - prefix_end - suffix_len
        new_changed_len = len(newContent) - prefix_end - suffix_len
        vivian_contribution = max(old_changed_len, new_changed_len)

    return {
        'contentHash': computeContentHash(newContent),
        'vivianContribution': existing_contribution + vivian_contribution,
        'mtime': mtime,
    }


async def getFileMtime(filePath):
    """Get a file's modification time (mtimeMs), falling back to Date.now() if"""
    try:
        return os.stat(expandFilePath(filePath)).st_mtime * 1000
    except Exception:
        return time.time() * 1000


def trackFileModification(state, filePath, oldContent, newContent, _userModified, mtime=None):
    """Track a file modification by vivian."""
    current_state = dict(state or createEmptyAttributionState())
    normalized_path = normalizeFilePath(filePath)
    file_states = dict(current_state.get('fileStates') or {})
    new_file_state = computeFileModificationState(
        file_states,
        filePath,
        oldContent or '',
        newContent or '',
        mtime if mtime is not None else time.time() * 1000,
    )
    file_states[normalized_path] = new_file_state
    current_state['fileStates'] = file_states
    return current_state


def trackFileCreation(state, filePath, content, mtime=None):
    """Track a file creation by vivian (e.g., via bash command)."""
    return trackFileModification(state, filePath, '', content, False, mtime)


def trackFileDeletion(state, filePath, oldContent):
    """Track a file deletion by vivian (e.g., via bash rm command)."""
    result = None
    _input = state
    _output = _input if _input is not None else {}
    return _output


def trackBulkFileChanges(state, changes=None):
    """Track multiple file changes in bulk, mutating a single Map copy."""
    result = None
    _input = state
    _output = _input if _input is not None else {}
    return _output


async def calculateCommitAttribution(states, stagedFiles):
    """Calculate final attribution for staged files."""
    files: dict[str, Any] = {}
    excluded_generated: list[str] = []
    surfaces: set[str] = set()
    surface_counts: dict[str, int] = {}

    total_vivian_chars = 0
    total_human_chars = 0

    merged_file_states: dict[str, dict[str, Any]] = {}
    for state in states or []:
        if not isinstance(state, dict):
            continue
        surface = str(state.get('surface') or getClientSurface())
        surfaces.add(surface)
        file_states = state.get('fileStates') or {}
        if not isinstance(file_states, dict):
            continue
        for path, file_state in file_states.items():
            if not isinstance(file_state, dict):
                continue
            existing = merged_file_states.get(path)
            if existing:
                merged_file_states[path] = {
                    **file_state,
                    'vivianContribution': int(existing.get('vivianContribution') or 0) + int(file_state.get('vivianContribution') or 0),
                    'surface': existing.get('surface') or surface,
                }
            else:
                merged_file_states[path] = {
                    **file_state,
                    'surface': surface,
                }

    effective_files = list(stagedFiles or merged_file_states.keys())
    for file_path in effective_files:
        normalized_path = normalizeFilePath(file_path)
        file_state = merged_file_states.get(normalized_path) or merged_file_states.get(file_path)
        if not isinstance(file_state, dict):
            continue
        abs_path = expandFilePath(file_path)
        vivian_chars = max(0, int(file_state.get('vivianContribution') or 0))
        human_chars = 0
        if os.path.exists(abs_path):
            try:
                total_size = os.stat(abs_path).st_size
                human_chars = max(0, total_size - vivian_chars)
            except Exception:
                human_chars = 0
        total = vivian_chars + human_chars
        percent = round((vivian_chars / total) * 100) if total > 0 else 0
        surface = str(file_state.get('surface') or next(iter(surfaces), getClientSurface()))
        files[normalized_path] = {
            'vivianChars': vivian_chars,
            'humanChars': human_chars,
            'percent': percent,
            'surface': surface,
        }
        total_vivian_chars += vivian_chars
        total_human_chars += human_chars
        surface_counts[surface] = (surface_counts.get(surface) or 0) + vivian_chars

    total_chars = total_vivian_chars + total_human_chars
    vivian_percent = round((total_vivian_chars / total_chars) * 100) if total_chars > 0 else 0
    surface_breakdown = {}
    for surface, chars in surface_counts.items():
        surface_breakdown[surface] = {
            'vivianChars': chars,
            'percent': round((chars / total_chars) * 100) if total_chars > 0 else 0,
        }

    return {
        'version': 1,
        'summary': {
            'vivianPercent': vivian_percent,
            'vivianChars': total_vivian_chars,
            'humanChars': total_human_chars,
            'surfaces': list(surfaces),
        },
        'files': files,
        'surfaceBreakdown': surface_breakdown,
        'excludedGenerated': excluded_generated,
        'sessions': [str(getSessionId())],
    }


async def getGitDiffSize(filePath):
    """Get the size of changes for a file from git diff."""
    cwd = getAttributionRepoRoot()
    try:
        result = subprocess.run(
            ['git', 'diff', '--cached', '--stat', '--', str(filePath)],
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=5,
        )
        if result.returncode != 0 or not result.stdout:
            return 0
        total_changes = 0
        for line in result.stdout.splitlines():
            if 'file changed' in line or 'files changed' in line:
                insert_match = re.search(r'(\d+) insertions?', line)
                delete_match = re.search(r'(\d+) deletions?', line)
                insertions = int(insert_match.group(1)) if insert_match else 0
                deletions = int(delete_match.group(1)) if delete_match else 0
                total_changes += (insertions + deletions) * 40
        return total_changes
    except Exception:
        return 0


async def isFileDeleted(filePath):
    """Check if a file was deleted in the staged changes."""
    cwd = getAttributionRepoRoot()
    try:
        result = subprocess.run(
            ['git', 'diff', '--cached', '--name-status', '--', str(filePath)],
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=5,
        )
        return result.returncode == 0 and result.stdout.strip().startswith('D\t')
    except Exception:
        return False


async def getStagedFiles():
    """Get staged files from git."""
    cwd = getAttributionRepoRoot()
    try:
        result = subprocess.run(
            ['git', 'diff', '--cached', '--name-only'],
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout:
            return [line for line in result.stdout.splitlines() if line]
    except Exception:
        pass
    return []


async def isGitTransientState():
    """Check if we're in a transient git state (rebase, merge, cherry-pick)."""
    cwd = getAttributionRepoRoot()
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--git-dir'],
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=5,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return False
        git_dir = result.stdout.strip()
        if not os.path.isabs(git_dir):
            git_dir = os.path.join(cwd, git_dir)
        for indicator in ('rebase-merge', 'rebase-apply', 'MERGE_HEAD', 'CHERRY_PICK_HEAD', 'BISECT_LOG'):
            if os.path.exists(os.path.join(git_dir, indicator)):
                return True
        return False
    except Exception:
        return False


def stateToSnapshotMessage(state, messageId):
    """Convert attribution state to snapshot message for persistence."""
    state = state if isinstance(state, dict) else createEmptyAttributionState()
    file_states = state.get('fileStates') or {}
    return {
        'type': 'attribution-snapshot',
        'messageId': messageId,
        'surface': state.get('surface') or getClientSurface(),
        'fileStates': dict(file_states) if isinstance(file_states, dict) else {},
        'promptCount': int(state.get('promptCount') or 0),
        'promptCountAtLastCommit': int(state.get('promptCountAtLastCommit') or 0),
        'permissionPromptCount': int(state.get('permissionPromptCount') or 0),
        'permissionPromptCountAtLastCommit': int(state.get('permissionPromptCountAtLastCommit') or 0),
        'escapeCount': int(state.get('escapeCount') or 0),
        'escapeCountAtLastCommit': int(state.get('escapeCountAtLastCommit') or 0),
    }


def restoreAttributionStateFromSnapshots(snapshots):
    """Restore attribution state from snapshot messages."""
    state = createEmptyAttributionState()
    if not isinstance(snapshots, list) or not snapshots:
        return state

    last_snapshot = snapshots[-1]
    if not isinstance(last_snapshot, dict):
        return state

    state['surface'] = last_snapshot.get('surface') or state['surface']

    file_states = last_snapshot.get('fileStates') or {}
    if isinstance(file_states, dict):
        state['fileStates'] = dict(file_states)

    state['promptCount'] = int(last_snapshot.get('promptCount') or 0)
    state['promptCountAtLastCommit'] = int(last_snapshot.get('promptCountAtLastCommit') or 0)
    state['permissionPromptCount'] = int(last_snapshot.get('permissionPromptCount') or 0)
    state['permissionPromptCountAtLastCommit'] = int(last_snapshot.get('permissionPromptCountAtLastCommit') or 0)
    state['escapeCount'] = int(last_snapshot.get('escapeCount') or 0)
    state['escapeCountAtLastCommit'] = int(last_snapshot.get('escapeCountAtLastCommit') or 0)
    return state


def attributionRestoreStateFromLog(attributionSnapshots, onUpdateState=None):
    """Restore attribution state from log snapshots on session resume."""
    state = restoreAttributionStateFromSnapshots(attributionSnapshots)
    if callable(onUpdateState):
        onUpdateState(state)
        return None
    return state


def incrementPromptCount(attribution, saveSnapshot=None):
    """Increment promptCount and save an attribution snapshot."""
    current = dict(attribution or createEmptyAttributionState())
    current['promptCount'] = int(current.get('promptCount') or 0) + 1
    snapshot = stateToSnapshotMessage(current, str(uuid.uuid4()))
    if callable(saveSnapshot):
        saveSnapshot(snapshot)
    return current

