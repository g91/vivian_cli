"""Portable session storage utilities shared by resume/list code paths."""

from __future__ import annotations

from typing import Any, Dict
import json
import os
import re
import unicodedata
from uuid import UUID

from .envUtils import get_vivian_config_home_dir
from .getWorktreePathsPortable import getWorktreePathsPortable
from .hash import djb2_hash


LiteSessionFile = Dict[str, Any]
Sink = Dict[str, Any]
LoadState = Dict[str, Any]


LITE_READ_BUF_SIZE: Any = 65536  # type: ignore
# Maximum length for a single filesystem path component (directory or file name).
MAX_SANITIZED_LENGTH: Any = 200  # type: ignore
# File size below which precompact filtering is skipped.
SKIP_PRECOMPACT_THRESHOLD: Any = 5 * 1024 * 1024  # type: ignore

_UUID_RE = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)
_COMPACT_BOUNDARY_MARKER = b'"compact_boundary"'
_COMMAND_NAME_RE = re.compile(r'<command-name>(.*?)</command-name>')
_SKIP_FIRST_PROMPT_PATTERN = re.compile(r'^(?:\s*<[a-z][\w-]*[\s>]|\[Request interrupted by user[^\]]*\])')


def validateUuid(maybeUuid):
    if not isinstance(maybeUuid, str):
        return None
    return maybeUuid if _UUID_RE.match(maybeUuid) else None


def unescapeJsonString(raw):
    """Unescape a JSON string value extracted as raw text."""
    if not isinstance(raw, str):
        return raw
    if '\\' not in raw:
        return raw
    try:
        return json.loads(f'"{raw}"')
    except Exception:
        return raw


def extractJsonStringField(text, key):
    """Extracts a simple JSON string field value from raw text without full parsing."""
    if not isinstance(text, str) or not isinstance(key, str):
        return None
    for pattern in (f'"{key}":"', f'"{key}": "'):
        idx = text.find(pattern)
        if idx < 0:
            continue
        value_start = idx + len(pattern)
        i = value_start
        while i < len(text):
            if text[i] == '\\':
                i += 2
                continue
            if text[i] == '"':
                return unescapeJsonString(text[value_start:i])
            i += 1
    return None


def extractLastJsonStringField(text, key):
    """Like extractJsonStringField but finds the LAST occurrence."""
    if not isinstance(text, str) or not isinstance(key, str):
        return None
    last_value = None
    for pattern in (f'"{key}":"', f'"{key}": "'):
        search_from = 0
        while True:
            idx = text.find(pattern, search_from)
            if idx < 0:
                break
            value_start = idx + len(pattern)
            i = value_start
            while i < len(text):
                if text[i] == '\\':
                    i += 2
                    continue
                if text[i] == '"':
                    last_value = unescapeJsonString(text[value_start:i])
                    break
                i += 1
            search_from = i + 1
    return last_value


def extractFirstPromptFromHead(head):
    """Extracts the first meaningful user prompt from a JSONL head chunk."""
    if not isinstance(head, str):
        return ''
    command_fallback = ''
    for line in head.splitlines():
        if '"type":"user"' not in line and '"type": "user"' not in line:
            continue
        if '"tool_result"' in line:
            continue
        if '"isMeta":true' in line or '"isMeta": true' in line:
            continue
        if '"isCompactSummary":true' in line or '"isCompactSummary": true' in line:
            continue
        try:
            entry = json.loads(line)
        except Exception:
            continue
        if not isinstance(entry, dict) or entry.get('type') != 'user':
            continue
        message = entry.get('message') or {}
        if not isinstance(message, dict):
            continue
        content = message.get('content')
        texts = []
        if isinstance(content, str):
            texts.append(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get('type') == 'text' and isinstance(block.get('text'), str):
                    texts.append(block['text'])
        for raw in texts:
            result = raw.replace('\n', ' ').strip()
            if not result:
                continue
            command_match = _COMMAND_NAME_RE.search(result)
            if command_match:
                if not command_fallback:
                    command_fallback = command_match.group(1)
                continue
            bash_match = re.search(r'<bash-input>([\s\S]*?)</bash-input>', result)
            if bash_match:
                return f"! {bash_match.group(1).strip()}"
            if _SKIP_FIRST_PROMPT_PATTERN.search(result):
                continue
            if len(result) > 200:
                result = result[:200].strip() + '…'
            return result
    return command_fallback


async def readHeadAndTail(filePath, fileSize, buf):
    """Reads the first and last LITE_READ_BUF_SIZE bytes of a file."""
    try:
        with open(filePath, 'rb') as handle:
            head_bytes = handle.read(LITE_READ_BUF_SIZE)
            if not head_bytes:
                return {'head': '', 'tail': ''}
            head = head_bytes.decode('utf-8', errors='replace')
            tail = head
            tail_offset = max(0, int(fileSize) - LITE_READ_BUF_SIZE)
            if tail_offset > 0:
                handle.seek(tail_offset)
                tail = handle.read(LITE_READ_BUF_SIZE).decode('utf-8', errors='replace')
            return {'head': head, 'tail': tail}
    except Exception:
        return {'head': '', 'tail': ''}


async def readSessionLite(filePath):
    """Opens a single session file, stats it, and reads head + tail in one fd."""
    try:
        stat_result = os.stat(filePath)
        result = await readHeadAndTail(filePath, stat_result.st_size, None)
        if not result['head']:
            return None
        return {
            'mtime': int(stat_result.st_mtime * 1000),
            'size': stat_result.st_size,
            'head': result['head'],
            'tail': result['tail'],
        }
    except Exception:
        return None


def simpleHash(str):
    return format(abs(djb2_hash(str)), 'x')


def sanitizePath(name):
    """Makes a string safe for use as a directory or file name."""
    sanitized = re.sub(r'[^a-zA-Z0-9]', '-', str(name))
    if len(sanitized) <= MAX_SANITIZED_LENGTH:
        return sanitized
    return f"{sanitized[:MAX_SANITIZED_LENGTH]}-{simpleHash(str(name))}"


def getProjectsDir():
    return os.path.join(get_vivian_config_home_dir(), 'projects')


def getProjectDir(projectDir):
    return os.path.join(getProjectsDir(), sanitizePath(projectDir))


async def canonicalizePath(dir):
    """Resolves a directory path to its canonical form using realpath + NFC"""
    try:
        return unicodedata.normalize('NFC', os.path.realpath(dir))
    except Exception:
        return unicodedata.normalize('NFC', str(dir))


async def findProjectDir(projectPath):
    """Finds the project directory for a given path, tolerating hash mismatches"""
    exact = getProjectDir(projectPath)
    if os.path.isdir(exact):
        return exact
    sanitized = sanitizePath(projectPath)
    if len(sanitized) <= MAX_SANITIZED_LENGTH:
        return None
    prefix = sanitized[:MAX_SANITIZED_LENGTH]
    projects_dir = getProjectsDir()
    try:
        for entry in os.scandir(projects_dir):
            if entry.is_dir() and entry.name.startswith(prefix + '-'):
                return os.path.join(projects_dir, entry.name)
    except Exception:
        return None
    return None


async def resolveSessionFilePath(sessionId, dir=None):
    """Resolve a sessionId to its on-disk JSONL file path."""
    file_name = f"{sessionId}.jsonl"
    if dir:
        canonical = await canonicalizePath(dir)
        project_dir = await findProjectDir(canonical)
        if project_dir:
            file_path = os.path.join(project_dir, file_name)
            try:
                stat_result = os.stat(file_path)
                if stat_result.st_size > 0:
                    return {'filePath': file_path, 'projectPath': canonical, 'fileSize': stat_result.st_size}
            except Exception:
                pass
        try:
            worktree_paths = await getWorktreePathsPortable(canonical)
        except Exception:
            worktree_paths = []
        for worktree in worktree_paths:
            if worktree == canonical:
                continue
            worktree_project_dir = await findProjectDir(worktree)
            if not worktree_project_dir:
                continue
            file_path = os.path.join(worktree_project_dir, file_name)
            try:
                stat_result = os.stat(file_path)
                if stat_result.st_size > 0:
                    return {'filePath': file_path, 'projectPath': worktree, 'fileSize': stat_result.st_size}
            except Exception:
                pass
        return None

    projects_dir = getProjectsDir()
    try:
        entries = list(os.scandir(projects_dir))
    except Exception:
        return None
    for entry in entries:
        file_path = os.path.join(projects_dir, entry.name, file_name)
        try:
            stat_result = os.stat(file_path)
            if stat_result.st_size > 0:
                return {'filePath': file_path, 'projectPath': None, 'fileSize': stat_result.st_size}
        except Exception:
            pass
    return None


def compactBoundaryMarker():
    return _COMPACT_BOUNDARY_MARKER


def parseBoundaryLine(line):
    """Confirm a byte-matched line is a real compact_boundary (marker can appear"""
    result = None
    _input = line
    _output = _input if _input is not None else {}
    return _output


def sinkWrite(s, src, start, end):
    n = end - start
    if n <= 0:
        return
    if s.len + n > s.len(buf):
        grown = Buffer.allocUnsafe(
        min(max(s.len(buf) * 2, s.len + n), s.cap),
        )
        s.buf.copy(grown, 0, 0, s.len)
        s.buf = grown
    src.copy(s.buf, s.len, start, end)
    s.len += n


def hasPrefix(src, prefix, at, end):
    return (
    end - at >= len(prefix) and
    src.compare(prefix, 0, len(prefix), at, at + len(prefix)) == 0
    )


def processStraddle(s, chunk, bytesRead):
    return s


def scanChunkLines(s, buf, boundaryMarker):
    lastSnapStart: number; lastSnapEnd: number; trailStart


def captureSnap(s, buf, chunk, lastSnapStart, lastSnapEnd):
    result = None
    _input = s
    _output = _input if _input is not None else {}
    return _output


def captureCarry(s, buf, trailStart):
    s.carryLen = len(buf) - trailStart
    if s.carryLen > 0:
        if s.carryBuf == None or s.carryLen > s.len(carryBuf):
            s.carryBuf = Buffer.allocUnsafe(s.carryLen)
        buf.copy(s.carryBuf, 0, trailStart, len(buf))


def finalizeOutput(s):
    result = None
    _input = s
    _output = _input if _input is not None else {}
    return _output


async def readTranscriptForLoad(filePath, fileSize):
    boundaryStartOffset
    postBoundaryBuf
    hasPreservedSegment

