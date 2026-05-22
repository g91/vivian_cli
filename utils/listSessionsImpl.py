"""
Port of src/utils/listSessionsImpl.ts
"""
from __future__ import annotations

from typing import Any, Dict
from functools import cmp_to_key
import os
import os.path
import asyncio
from datetime import datetime, timezone, timedelta
import platform

from .sessionStoragePortable import (
    MAX_SANITIZED_LENGTH,
    canonicalizePath,
    extractFirstPromptFromHead,
    extractJsonStringField,
    extractLastJsonStringField,
    findProjectDir,
    getProjectsDir,
    readSessionLite,
    resolveSessionFilePath,
    sanitizePath,
    validateUuid,
)
from .getWorktreePathsPortable import getWorktreePathsPortable


SessionInfo = Dict[str, Any]
ListSessionsOptions = Dict[str, Any]
Candidate = Dict[str, Any]
READ_BATCH_SIZE = 32


def parseSessionInfoFromLite(sessionId, lite, projectPath=None):
    """Parses SessionInfo fields from a lite session read (head/tail/stat).
Returns null for sidechain sessions or metadata-only sessions with no
extractable summary.

Exported for reuse by getSessionInfoImpl."""
    if not isinstance(sessionId, str) or not isinstance(lite, dict):
        return None

    head = lite.get('head') or ''
    tail = lite.get('tail') or ''
    mtime = lite.get('mtime')
    size = lite.get('size')

    first_newline = head.find('\n')
    first_line = head[:first_newline] if first_newline >= 0 else head
    if '"isSidechain":true' in first_line or '"isSidechain": true' in first_line:
        return None

    custom_title = (
        extractLastJsonStringField(tail, 'customTitle')
        or extractLastJsonStringField(head, 'customTitle')
        or extractLastJsonStringField(tail, 'aiTitle')
        or extractLastJsonStringField(head, 'aiTitle')
    )
    first_prompt = extractFirstPromptFromHead(head) or None

    first_timestamp = extractJsonStringField(head, 'timestamp')
    created_at = None
    if first_timestamp:
        try:
            created_at = int(datetime.fromisoformat(first_timestamp.replace('Z', '+00:00')).timestamp() * 1000)
        except Exception:
            created_at = None

    summary = (
        custom_title
        or extractLastJsonStringField(tail, 'lastPrompt')
        or extractLastJsonStringField(tail, 'summary')
        or first_prompt
    )
    if not summary:
        return None

    git_branch = (
        extractLastJsonStringField(tail, 'gitBranch')
        or extractJsonStringField(head, 'gitBranch')
        or None
    )
    session_cwd = extractJsonStringField(head, 'cwd') or projectPath or None

    tag = None
    for line in reversed(tail.splitlines()):
        if line.startswith('{"type":"tag"'):
            tag = extractLastJsonStringField(line, 'tag') or None
            break

    return {
        'sessionId': sessionId,
        'summary': summary,
        'lastModified': mtime,
        'fileSize': size,
        'customTitle': custom_title,
        'firstPrompt': first_prompt,
        'gitBranch': git_branch,
        'cwd': session_cwd,
        'tag': tag,
        'createdAt': created_at,
    }


async def listCandidates(projectDir, doStat, projectPath=None):
    try:
        names = os.listdir(projectDir)
    except Exception:
        return []

    results: list[Candidate] = []
    for name in names:
        if not name.endswith('.jsonl'):
            continue
        session_id = validateUuid(name[:-6])
        if not session_id:
            continue
        file_path = os.path.join(projectDir, name)
        if not doStat:
            results.append({
                'sessionId': session_id,
                'filePath': file_path,
                'mtime': 0,
                'projectPath': projectPath,
            })
            continue
        try:
            stat_result = os.stat(file_path)
        except Exception:
            continue
        results.append({
            'sessionId': session_id,
            'filePath': file_path,
            'mtime': int(stat_result.st_mtime * 1000),
            'projectPath': projectPath,
        })
    return results


async def readCandidate(candidate):
    lite = await readSessionLite(candidate['filePath'])
    if not lite:
        return None

    info = parseSessionInfoFromLite(
        candidate['sessionId'],
        lite,
        candidate.get('projectPath'),
    )
    if not info:
        return None
    if candidate.get('mtime'):
        info['lastModified'] = candidate['mtime']
    return info


def compareDesc(a, b):
    if b['mtime'] != a['mtime']:
        return b['mtime'] - a['mtime']
    if b['sessionId'] < a['sessionId']:
        return -1
    if b['sessionId'] > a['sessionId']:
        return 1
    return 0


async def applySortAndLimit(candidates, limit, offset):
    candidates.sort(key=cmp_to_key(compareDesc))

    sessions = []
    want = limit if isinstance(limit, int) and limit > 0 else float('inf')
    skipped = 0
    seen = set()

    index = 0
    while index < len(candidates) and len(sessions) < want:
        batch = candidates[index:index + READ_BATCH_SIZE]
        results = await asyncio.gather(*(readCandidate(candidate) for candidate in batch))
        for result in results:
            index += 1
            if not result:
                continue
            if result['sessionId'] in seen:
                continue
            seen.add(result['sessionId'])
            if skipped < offset:
                skipped += 1
                continue
            sessions.append(result)
            if len(sessions) >= want:
                break

    return sessions


async def readAllAndSort(candidates):
    all_results = await asyncio.gather(*(readCandidate(candidate) for candidate in candidates))
    by_id = {}
    for session in all_results:
        if not session:
            continue
        existing = by_id.get(session['sessionId'])
        if not existing or session['lastModified'] > existing['lastModified']:
            by_id[session['sessionId']] = session
    sessions = list(by_id.values())
    sessions.sort(
        key=cmp_to_key(
            lambda a, b: (
                b['lastModified'] - a['lastModified']
                if b['lastModified'] != a['lastModified']
                else (-1 if b['sessionId'] < a['sessionId'] else 1 if b['sessionId'] > a['sessionId'] else 0)
            )
        )
    )
    return sessions


async def gatherProjectCandidates(dir, includeWorktrees, doStat):
    canonical_dir = await canonicalizePath(dir)

    worktree_paths = []
    if includeWorktrees:
        try:
            worktree_paths = await getWorktreePathsPortable(canonical_dir)
        except Exception:
            worktree_paths = []

    if len(worktree_paths) <= 1:
        project_dir = await findProjectDir(canonical_dir)
        if not project_dir:
            return []
        return await listCandidates(project_dir, doStat, canonical_dir)

    projects_dir = getProjectsDir()
    case_insensitive = platform.system().lower().startswith('win')

    indexed = []
    for worktree_path in worktree_paths:
        sanitized = sanitizePath(worktree_path)
        indexed.append({
            'path': worktree_path,
            'prefix': sanitized.lower() if case_insensitive else sanitized,
        })
    indexed.sort(key=lambda item: len(item['prefix']), reverse=True)

    try:
        all_dirents = [entry for entry in os.scandir(projects_dir) if entry.is_dir()]
    except Exception:
        project_dir = await findProjectDir(canonical_dir)
        if not project_dir:
            return []
        return await listCandidates(project_dir, doStat, canonical_dir)

    all_candidates = []
    seen_dirs = set()

    canonical_project_dir = await findProjectDir(canonical_dir)
    if canonical_project_dir:
        dir_base = os.path.basename(canonical_project_dir)
        seen_dirs.add(dir_base.lower() if case_insensitive else dir_base)
        all_candidates.extend(await listCandidates(canonical_project_dir, doStat, canonical_dir))

    for dirent in all_dirents:
        dir_name = dirent.name.lower() if case_insensitive else dirent.name
        if dir_name in seen_dirs:
            continue
        for indexed_worktree in indexed:
            prefix = indexed_worktree['prefix']
            is_match = (
                dir_name == prefix
                or (len(prefix) >= MAX_SANITIZED_LENGTH and dir_name.startswith(prefix + '-'))
            )
            if is_match:
                seen_dirs.add(dir_name)
                all_candidates.extend(
                    await listCandidates(
                        os.path.join(projects_dir, dirent.name),
                        doStat,
                        indexed_worktree['path'],
                    )
                )
                break

    return all_candidates


async def gatherAllCandidates(doStat):
    projects_dir = getProjectsDir()
    try:
        dirents = [entry for entry in os.scandir(projects_dir) if entry.is_dir()]
    except Exception:
        return []
    per_project = await asyncio.gather(
        *(listCandidates(os.path.join(projects_dir, dirent.name), doStat) for dirent in dirents)
    )
    flattened = []
    for project_candidates in per_project:
        flattened.extend(project_candidates)
    return flattened


async def listSessionsImpl(options=None):
    options = options or {}
    dir = options.get('dir')
    limit = options.get('limit')
    offset = int(options.get('offset', 0) or 0)
    include_worktrees = options.get('includeWorktrees', True)
    do_stat = (isinstance(limit, int) and limit > 0) or offset > 0

    if dir:
        candidates = await gatherProjectCandidates(dir, include_worktrees, do_stat)
    else:
        candidates = await gatherAllCandidates(do_stat)

    if not do_stat:
        return await readAllAndSort(candidates)
    return await applySortAndLimit(candidates, limit, offset)


async def getSessionInfoImpl(sessionId, options=None):
    options = options or {}
    resolved = await resolveSessionFilePath(sessionId, options.get('dir'))
    if not resolved:
        return None
    lite = await readSessionLite(resolved['filePath'])
    if not lite:
        return None
    return parseSessionInfoFromLite(sessionId, lite, resolved.get('projectPath'))

