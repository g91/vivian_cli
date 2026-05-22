"""File utilities — mirrors src/utils/file.ts."""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
import os
import os.path
import re
import asyncio
import time
from datetime import datetime, timezone, timedelta
import platform
import math
from enum import Enum, auto
import struct

from .cwd import get_cwd
from .platform import get_platform


File = Dict[str, Any]


MAX_OUTPUT_SIZE = int(0.25 * 1024 * 1024)
# Marker included in file-not-found error messages that contain a cwd note.
FILE_NOT_FOUND_CWD_NOTE: Any = 'Note: your current working directory is'  # type: ignore


async def pathExists(path):
    """Check if a path exists asynchronously."""
    if path is None:
        return False
    return await asyncio.to_thread(os.path.exists, path)


def readFileSafe(filepath):
    try:
        with open(filepath, "r", encoding="utf-8", newline="") as handle:
            return handle.read()
    except Exception:
        return None


def getFileModificationTime(filePath):
    """Get the normalized modification time of a file in milliseconds."""
    return math.floor(os.stat(filePath).st_mtime_ns / 1_000_000)


async def getFileModificationTimeAsync(filePath):
    """Async variant of getFileModificationTime. Same floor semantics."""
    stat_result = await asyncio.to_thread(os.stat, filePath)
    return math.floor(stat_result.st_mtime_ns / 1_000_000)


def writeTextContent(filePath, content, encoding, endings):
    toWrite = content
    if endings == 'CRLF':
        # Normalize any existing CRLF to LF first so a new_string that already
        # contains \r\n (raw model output) doesn't become \r\r\n after the join.
        toWrite = content.replace('\r\n', '\n').replace('\n', '\r\n')
    writeFileSyncAndFlush_DEPRECATED(filePath, toWrite, {"encoding": encoding})


def detectFileEncoding(filePath):
    try:
        with open(filePath, "rb") as handle:
            prefix = handle.read(4)
        if prefix.startswith(b"\xff\xfe") or prefix.startswith(b"\xfe\xff"):
            return "utf-16"
        if prefix.startswith(b"\xef\xbb\xbf"):
            return "utf-8-sig"
    except Exception:
        pass
    return "utf8"


def detectLineEndings(filePath, encoding='utf8'):
    try:
        with open(filePath, "rb") as handle:
            content = handle.read(4096)
    except Exception:
        return 'LF'
    if b'\r\n' in content:
        return 'CRLF'
    return 'LF'


def convertLeadingTabsToSpaces(content):
    if '\t' not in content:
        return content
    return re.sub(r'^\t+', lambda match: '  ' * len(match.group(0)), content, flags=re.MULTILINE)


def getAbsoluteAndRelativePaths(path):
    absolutePath = os.path.abspath(os.path.expanduser(path)) if path else None
    relativePath = os.path.relpath(absolutePath, get_cwd()) if absolutePath else None
    return {"absolutePath": absolutePath, "relativePath": relativePath}


def getDisplayPath(filePath):
    paths = getAbsoluteAndRelativePaths(filePath)
    relative_path = paths.get("relativePath")
    if relative_path and not str(relative_path).startswith(".."):
        return str(relative_path)

    home_dir = os.path.expanduser("~")
    absolute_path = str(paths.get("absolutePath") or filePath)
    home_prefix = home_dir + os.sep
    if absolute_path.startswith(home_prefix):
        return "~" + absolute_path[len(home_dir):]

    return absolute_path


def findSimilarFile(filePath):
    """Find files with the same name but different extensions in the same directory"""
    try:
        directory = os.path.dirname(filePath)
        base_name = os.path.splitext(os.path.basename(filePath))[0]
        for entry in os.scandir(directory):
            if not entry.is_file():
                continue
            candidate_base = os.path.splitext(entry.name)[0]
            candidate_path = os.path.join(directory, entry.name)
            if candidate_base == base_name and os.path.abspath(candidate_path) != os.path.abspath(filePath):
                return entry.name
    except FileNotFoundError:
        return None
    except Exception:
        return None
    return None


async def suggestPathUnderCwd(requestedPath):
    """Suggests a corrected path under the current working directory when a file/directory"""
    cwd = os.getcwd()
    cwd_parent = os.path.dirname(cwd)

    resolved_path = requestedPath
    try:
        resolved_dir = await asyncio.to_thread(os.path.realpath, os.path.dirname(requestedPath))
        resolved_path = os.path.join(resolved_dir, os.path.basename(requestedPath))
    except Exception:
        pass

    cwd_parent_prefix = cwd_parent if cwd_parent == os.sep else cwd_parent + os.sep
    if (
        not resolved_path.startswith(cwd_parent_prefix)
        or resolved_path.startswith(cwd + os.sep)
        or resolved_path == cwd
    ):
        return None

    rel_from_parent = os.path.relpath(resolved_path, cwd_parent)
    corrected_path = os.path.join(cwd, rel_from_parent)
    if await asyncio.to_thread(os.path.exists, corrected_path):
        return corrected_path
    return None


def isCompactLinePrefixEnabled():
    """Whether to use the compact line-number prefix format (`N\\t` instead of"""
    return True


def addLineNumbers(__content_____1_indexed_startLine___):
    """Adds cat -n style line numbers to the content."""
    content = __content_____1_indexed_startLine___.get("content", "")
    startLine = int(__content_____1_indexed_startLine___.get("startLine", 1))
    if not content:
        return ""
    lines = re.split(r'\r?\n', content)
    if isCompactLinePrefixEnabled():
        return '\n'.join(f"{index + startLine}\t{line}" for index, line in enumerate(lines))
    rendered = []
    for index, line in enumerate(lines):
        num = str(index + startLine)
        rendered.append(f"{num}→{line}" if len(num) >= 6 else f"{num.rjust(6, ' ')}→{line}")
    return '\n'.join(rendered)


def stripLineNumberPrefix(line):
    """Inverse of addLineNumbers -- strips the `N->` or `N\\t` prefix from a single"""
    match = re.match(r'^\s*\d+[→\t](.*)$', line)
    return match.group(1) if match else line


def isDirEmpty(dirPath):
    """Checks if a directory is empty."""
    try:
        with os.scandir(dirPath) as entries:
            return next(entries, None) is None
    except FileNotFoundError:
        return True
    except Exception:
        return False


def readFileSyncCached(filePath):
    """Reads a file with caching to avoid redundant I/O operations."""
    with open(filePath, "r", encoding="utf-8") as handle:
        return handle.read()


def writeFileSyncAndFlush_DEPRECATED(filePath, content, options=None):
    """Writes to a file and flushes the file to disk"""
    options = options or {"encoding": "utf-8"}
    encoding = options.get("encoding", "utf-8")
    mode = options.get("mode")
    parent = os.path.dirname(filePath)
    if parent:
        os.makedirs(parent, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    fd = os.open(filePath, flags, mode or 0o666)
    try:
        with os.fdopen(fd, "w", encoding=encoding, closefd=False) as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        os.close(fd)


def getDesktopPath():
    platform_name = get_platform()
    home_dir = os.path.expanduser('~')

    if platform_name == 'macos':
        return os.path.join(home_dir, 'Desktop')

    if platform_name in ('windows', 'wsl'):
        windows_home = os.environ.get('USERPROFILE')
        if windows_home:
            normalized_home = re.sub(r'\\+', '/', windows_home)
            wsl_path = re.sub(r'^[A-Z]:', '', normalized_home, flags=re.IGNORECASE)
            desktop_path = f'/mnt/c{wsl_path}/Desktop'
            if os.path.exists(desktop_path):
                return desktop_path

        try:
            users_dir = '/mnt/c/Users'
            for user in os.listdir(users_dir):
                if user in {'Public', 'Default', 'Default User', 'All Users'}:
                    continue
                potential_desktop_path = os.path.join(users_dir, user, 'Desktop')
                if os.path.exists(potential_desktop_path):
                    return potential_desktop_path
        except Exception:
            pass

    desktop_path = os.path.join(home_dir, 'Desktop')
    if os.path.exists(desktop_path):
        return desktop_path
    return home_dir


get_desktop_path = getDesktopPath


def isFileWithinReadSizeLimit(filePath, maxSizeBytes=MAX_OUTPUT_SIZE):
    """Validates that a file size is within the specified limit."""
    try:
        return os.stat(filePath).st_size <= maxSizeBytes
    except Exception:
        return False


def normalizePathForComparison(filePath):
    """Normalize a file path for comparison, handling platform differences."""
    normalized = os.path.normpath(filePath)
    if get_platform() == 'windows':
        normalized = normalized.replace('/', '\\').lower()
    return normalized


def pathsEqual(path1, path2):
    """Compare two file paths for equality, handling Windows case-insensitivity."""
    return normalizePathForComparison(path1) == normalizePathForComparison(path2)

