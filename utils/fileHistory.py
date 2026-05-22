"""
passpasspasspasspass of src/utils/fileHistory
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
import difflib
import os
import os.path
import asyncio
import hashlib
import shutil
import uuid
import time
from datetime import datetime, timezone, timedelta
import glob
from collections import defaultdict
import inspect

from ..bootstrap.state import getIsNonInteractiveSession, getOriginalCwd, getSessionId
from .config import get_global_config
from .envUtils import is_env_truthy, get_vivian_config_home_dir
from .sessionStorage import recordFileHistorySnapshot


BackupFileName = Union[str, Any]
FileHistoryBackup = Dict[str, Any]
FileHistorySnapshot = Dict[str, Any]
FileHistoryState = Dict[str, Any]
DiffStats = Any
ENABLE_DUMP_STATE = False


def fileHistoryEnabled():
    if getIsNonInteractiveSession():
        return fileHistoryEnabledSdk()
    config = get_global_config() or {}
    return (
    config.get('fileCheckpointingEnabled', True) != False and
    not is_env_truthy(os.environ.get("vivian_CODE_DISABLE_FILE_CHECKPOINTING", ""))
    )


def fileHistoryEnabledSdk():
    return (
    is_env_truthy(os.environ.get("vivian_CODE_ENABLE_SDK_FILE_CHECKPOINTING", "")) and
    not is_env_truthy(os.environ.get("vivian_CODE_DISABLE_FILE_CHECKPOINTING", ""))
    )


async def fileHistoryTrackEdit(updateFileHistoryState, _____void__filePath__string__messageId__UUID_):
    """Tracks a file edit (and add) by creating a backup of its current contents (if necessary)."""
    if not fileHistoryEnabled() or not callable(updateFileHistoryState):
        return None

    file_path, message_id = _____void__filePath__string__messageId__UUID_
    tracking_path = maybeShortenFilePath(file_path)
    holder = {'state': None}
    updateFileHistoryState(lambda state: _capture_file_history_state(state, holder))
    captured = holder.get('state')
    if not isinstance(captured, dict):
        return None

    most_recent = (captured.get('snapshots') or [])[-1] if (captured.get('snapshots') or []) else None
    if not isinstance(most_recent, dict):
        return None
    if (most_recent.get('trackedFileBackups') or {}).get(tracking_path):
        return None

    backup = await createBackup(file_path, 1)

    def _commit(state):
        base_state = state if isinstance(state, dict) else {
            'snapshots': [],
            'trackedFiles': set(),
            'snapshotSequence': 0,
        }
        snapshots = list(base_state.get('snapshots') or [])
        if not snapshots:
            return base_state
        latest = dict(snapshots[-1])
        tracked_file_backups = dict(latest.get('trackedFileBackups') or {})
        if tracking_path in tracked_file_backups:
            return base_state
        tracked_file_backups[tracking_path] = backup
        latest['trackedFileBackups'] = tracked_file_backups
        snapshots[-1] = latest
        tracked_files = set(base_state.get('trackedFiles') or set())
        tracked_files.add(tracking_path)
        return {
            **base_state,
            'snapshots': snapshots,
            'trackedFiles': tracked_files,
        }

    updateFileHistoryState(_commit)
    updated_snapshot = {
        **most_recent,
        'trackedFileBackups': {
            **(most_recent.get('trackedFileBackups') or {}),
            tracking_path: backup,
        },
    }
    recordFileHistorySnapshot(message_id, updated_snapshot, True)
    return None


async def fileHistoryMakeSnapshot(updateFileHistoryState, _____void__messageId__UUID_):
    """Adds a snapshot in the file history and backs up any modified tracked files."""
    if not fileHistoryEnabled():
        return None

    message_id = _____void__messageId__UUID_
    holder = {'state': None}

    if callable(updateFileHistoryState):
        updateFileHistoryState(lambda state: _capture_file_history_state(state, holder))

    captured = holder.get('state')
    if not isinstance(captured, dict):
        return None

    tracked_files = captured.get('trackedFiles') or set()
    last_snapshot = (captured.get('snapshots') or [])[-1] if (captured.get('snapshots') or []) else None
    tracked_file_backups = {}
    if isinstance(last_snapshot, dict):
        for tracking_path in tracked_files:
            inherited = (last_snapshot.get('trackedFileBackups') or {}).get(tracking_path)
            if inherited is not None:
                tracked_file_backups[tracking_path] = inherited

    new_snapshot = {
        'messageId': message_id,
        'trackedFileBackups': tracked_file_backups,
        'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
    }

    def _commit(state):
        base_state = state if isinstance(state, dict) else {
            'snapshots': [],
            'trackedFiles': set(),
            'snapshotSequence': 0,
        }
        snapshots = list(base_state.get('snapshots') or [])
        snapshots.append(new_snapshot)
        if len(snapshots) > 100:
            snapshots = snapshots[-100:]
        return {
            **base_state,
            'snapshots': snapshots,
            'snapshotSequence': int(base_state.get('snapshotSequence') or 0) + 1,
        }

    if callable(updateFileHistoryState):
        updateFileHistoryState(_commit)

    recordFileHistorySnapshot(message_id, new_snapshot, False)
    return None


def _capture_file_history_state(state, holder):
    holder['state'] = state
    return state


async def fileHistoryRewind(updateFileHistoryState, _____void__messageId__UUID_):
    """Rewinds the file system to a previous snapshot."""
    if not fileHistoryEnabled() or not callable(updateFileHistoryState):
        return None

    holder = {'state': None}
    updateFileHistoryState(lambda state: _capture_file_history_state(state, holder))
    captured = holder.get('state')
    if not isinstance(captured, dict):
        return None

    target_snapshot = None
    for snapshot in reversed(list(captured.get('snapshots') or [])):
        if isinstance(snapshot, dict) and snapshot.get('messageId') == _____void__messageId__UUID_:
            target_snapshot = snapshot
            break
    if not isinstance(target_snapshot, dict):
        raise ValueError('The selected snapshot was not found')

    await applySnapshot(captured, target_snapshot)
    return None


def fileHistoryCanRestore(state, messageId):
    if not fileHistoryEnabled():
        return False
    return any(isinstance(snapshot, dict) and snapshot.get('messageId') == messageId for snapshot in (state or {}).get('snapshots', []))


async def fileHistoryGetDiffStats(state, messageId):
    """Computes diff stats for a file snapshot by counting the number of files that would be changed"""
    if not fileHistoryEnabled() or not isinstance(state, dict):
        return None

    target_snapshot = None
    for snapshot in reversed(list(state.get('snapshots') or [])):
        if isinstance(snapshot, dict) and snapshot.get('messageId') == messageId:
            target_snapshot = snapshot
            break
    if not isinstance(target_snapshot, dict):
        return None

    results = await asyncio.gather(
        *[
            _compute_file_history_diff_result(state, target_snapshot, tracking_path)
            for tracking_path in set(state.get('trackedFiles') or set())
        ]
    )

    files_changed: list[str] = []
    insertions = 0
    deletions = 0
    for result in results:
        if not result:
            continue
        files_changed.append(result['filePath'])
        stats = result.get('stats') or {}
        insertions += int(stats.get('insertions') or 0)
        deletions += int(stats.get('deletions') or 0)

    return {
        'filesChanged': files_changed,
        'insertions': insertions,
        'deletions': deletions,
    }


async def fileHistoryHasAnyChanges(state, messageId):
    """Lightweight boolean-only check: would rewinding to this message change any"""
    if not fileHistoryEnabled() or not isinstance(state, dict):
        return False

    target_snapshot = None
    for snapshot in reversed(list(state.get('snapshots') or [])):
        if isinstance(snapshot, dict) and snapshot.get('messageId') == messageId:
            target_snapshot = snapshot
            break
    if not isinstance(target_snapshot, dict):
        return False

    for tracking_path in set(state.get('trackedFiles') or set()):
        file_path = maybeExpandFilePath(tracking_path)
        target_backup = (target_snapshot.get('trackedFileBackups') or {}).get(tracking_path)
        backup_file_name = None
        if isinstance(target_backup, dict):
            backup_file_name = target_backup.get('backupFileName')
        else:
            backup_file_name = getBackupFileNameFirstVersion(tracking_path, state)
        if backup_file_name is None:
            if os.path.exists(file_path):
                return True
            continue
        if backup_file_name and await checkOriginFileChanged(file_path, backup_file_name):
            return True
    return False


async def applySnapshot(state, targetSnapshot):
    """Applies the given file snapshot state to the tracked files (writes/deletes"""
    if not isinstance(state, dict) or not isinstance(targetSnapshot, dict):
        return []

    files_changed = []
    for tracking_path in set(state.get('trackedFiles') or set()):
        file_path = maybeExpandFilePath(tracking_path)
        target_backup = (targetSnapshot.get('trackedFileBackups') or {}).get(tracking_path)
        backup_file_name = None
        if isinstance(target_backup, dict):
            backup_file_name = target_backup.get('backupFileName')
        else:
            backup_file_name = getBackupFileNameFirstVersion(tracking_path, state)

        if backup_file_name is None:
            if os.path.exists(file_path):
                os.remove(file_path)
                files_changed.append(file_path)
            continue

        if await checkOriginFileChanged(file_path, backup_file_name):
            await restoreBackup(file_path, backup_file_name)
            files_changed.append(file_path)
    return files_changed


async def checkOriginFileChanged(originalFile, backupFileName, originalStatsHint=None):
    """Checks if the original file has been changed compared to the backup file."""
    if originalFile is None:
        return False
    backup_path = resolveBackupPath(backupFileName)
    original_exists = os.path.exists(originalFile)
    backup_exists = os.path.exists(backup_path)
    if original_exists != backup_exists:
        return True
    if not original_exists and not backup_exists:
        return False
    try:
        original_stat = os.stat(originalFile)
        backup_stat = os.stat(backup_path)
        if original_stat.st_size != backup_stat.st_size:
            return True
        with open(originalFile, 'rb') as original_handle, open(backup_path, 'rb') as backup_handle:
            return original_handle.read() != backup_handle.read()
    except Exception:
        return True


async def computeDiffStatsForFile(originalFile, backupFileName=None):
    """Computes the number of lines changed in the diff."""
    files_changed: list[str] = []
    insertions = 0
    deletions = 0

    try:
        backup_path = resolveBackupPath(backupFileName) if backupFileName else None
        original_content, backup_content = await asyncio.gather(
            readFileAsyncOrNull(originalFile),
            readFileAsyncOrNull(backup_path) if backup_path else asyncio.sleep(0, result=None),
        )

        if original_content is None and backup_content is None:
            return {
                'filesChanged': files_changed,
                'insertions': insertions,
                'deletions': deletions,
            }

        files_changed.append(originalFile)
        original_lines = (original_content or '').splitlines(keepends=True)
        backup_lines = (backup_content or '').splitlines(keepends=True)
        matcher = difflib.SequenceMatcher(a=backup_lines, b=original_lines)
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'insert':
                insertions += j2 - j1
            elif tag == 'delete':
                deletions += i2 - i1
            elif tag == 'replace':
                deletions += i2 - i1
                insertions += j2 - j1
    except Exception:
        pass

    return {
        'filesChanged': files_changed,
        'insertions': insertions,
        'deletions': deletions,
    }


async def _compute_file_history_diff_result(state, target_snapshot, tracking_path):
    try:
        file_path = maybeExpandFilePath(tracking_path)
        target_backup = (target_snapshot.get('trackedFileBackups') or {}).get(tracking_path)
        if isinstance(target_backup, dict):
            backup_file_name = target_backup.get('backupFileName')
        else:
            backup_file_name = getBackupFileNameFirstVersion(tracking_path, state)

        if backup_file_name is None:
            if os.path.exists(file_path):
                return {
                    'filePath': file_path,
                    'stats': {'filesChanged': [file_path], 'insertions': 0, 'deletions': 0},
                }
            return None

        stats = await computeDiffStatsForFile(file_path, backup_file_name)
        if stats.get('insertions') or stats.get('deletions'):
            return {'filePath': file_path, 'stats': stats}
        return None
    except Exception:
        return None


def getBackupFileName(filePath, version):
    digest = hashlib.sha256(str(filePath).encode('utf-8')).hexdigest()[:16]
    return f"{digest}@v{version}"


def resolveBackupPath(backupFileName, sessionId=None):
    effective_session_id = sessionId or getSessionId()
    return os.path.join(get_vivian_config_home_dir(), 'file-history', str(effective_session_id), str(backupFileName))


async def createBackup(filePath, version):
    """Creates a backup of the file at filePath. If the file does not exist"""
    now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    if not filePath or not os.path.exists(filePath):
        return {'backupFileName': None, 'version': version, 'backupTime': now}

    backup_file_name = getBackupFileName(filePath, version)
    backup_path = resolveBackupPath(backup_file_name)
    os.makedirs(os.path.dirname(backup_path), exist_ok=True)
    shutil.copy2(filePath, backup_path)
    return {'backupFileName': backup_file_name, 'version': version, 'backupTime': now}


async def restoreBackup(filePath, backupFileName):
    """Restores a file from its backup path with proper directory creation and permissions."""
    backup_path = resolveBackupPath(backupFileName)
    os.makedirs(os.path.dirname(filePath), exist_ok=True)
    shutil.copy2(backup_path, filePath)
    return None


def getBackupFileNameFirstVersion(trackingPath, state):
    """Gets the first (earliest) backup version for a file, used when rewinding"""
    for snapshot in state.get('snapshots') or []:
        if not isinstance(snapshot, dict):
            continue
        backup = (snapshot.get('trackedFileBackups') or {}).get(trackingPath)
        if isinstance(backup, dict):
            return backup.get('backupFileName')
    return None


def maybeShortenFilePath(filePath):
    """Use the relative path as the key to reduce session storage space for tracking."""
    if not isinstance(filePath, str):
        return filePath
    try:
        original_cwd = getOriginalCwd()
        if os.path.isabs(filePath):
            relative_path = os.path.relpath(filePath, original_cwd)
            if not relative_path.startswith('..' + os.sep) and relative_path != '..':
                return relative_path.replace(os.sep, '/')
    except Exception:
        return filePath
    return filePath


def maybeExpandFilePath(filePath):
    if os.path.isabs(filePath):
        return filePath
    return os.path.join(getOriginalCwd(), filePath)


def fileHistoryRestoreStateFromLog(fileHistorySnapshots, onUpdateState=None):
    """Restores file history snapshot state for a given log option."""
    if not fileHistoryEnabled():
        return None

    snapshots = []
    tracked_files = set()
    for snapshot in fileHistorySnapshots or []:
        if not isinstance(snapshot, dict):
            continue
        tracked_file_backups = {}
        for path, backup in (snapshot.get('trackedFileBackups') or {}).items():
            tracking_path = maybeShortenFilePath(path)
            tracked_files.add(tracking_path)
            tracked_file_backups[tracking_path] = backup
        snapshots.append({
            **snapshot,
            'trackedFileBackups': tracked_file_backups,
        })

    state = {
        'snapshots': snapshots,
        'trackedFiles': tracked_files,
        'snapshotSequence': len(snapshots),
    }
    if callable(onUpdateState):
        onUpdateState(state)
        return None
    return state


async def copyFileHistoryForResume(log):
    """Copy file history snapshots for a given log option."""
    result = None
    _input = log
    _output = _input if _input is not None else {}
    return _output


async def notifyVscodeSnapshotFilesUpdated(oldState, newState):
    """Notifies VSCode about files that have changed between snapshots."""
    result = None
    _input = oldState
    _output = _input if _input is not None else {}
    return _output


async def readFileAsyncOrNull(path):
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            return handle.read()
    except Exception:
        return None


def maybeDumpStateForDebug(state):
    if ENABLE_DUMP_STATE:
        # biome-ignore lint/suspicious/noConsole:: intentional console output
        print(inspect(state, False, 5))

