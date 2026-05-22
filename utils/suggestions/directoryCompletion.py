"""Port of src/utils/suggestions/directoryCompletion.ts - LRU-cached directory completions."""
from __future__ import annotations
from typing import Any, Optional, Dict, List
import os
import functools
import asyncio

DirectoryEntry = Dict[str, Any]
PathEntry = Dict[str, Any]
CompletionOptions = Dict[str, Any]
ParsedPath = Dict[str, Any]

# Simple LRU cache size
_CACHE_SIZE = 64
_dir_cache: Dict[str, List[str]] = {}
_path_cache: Dict[str, List[PathEntry]] = {}


def parse_partial_path(partial_path: str, base_path: Optional[str] = None) -> ParsedPath:
    """Parse a partial path into directory and prefix components."""
    if not base_path:
        base_path = os.getcwd()

    if partial_path in ('', '.'):
        return {'dir': base_path, 'prefix': '', 'isAbsolute': False}

    expanded = os.path.expanduser(partial_path)
    is_absolute = os.path.isabs(expanded)
    dir_part = os.path.dirname(expanded)
    prefix = os.path.basename(expanded)

    if not dir_part or dir_part == '.':
        dir_part = base_path
    elif not is_absolute:
        dir_part = os.path.join(base_path, dir_part)

    return {'dir': os.path.normpath(dir_part), 'prefix': prefix, 'isAbsolute': is_absolute}


parsePartialPath = parse_partial_path


async def scan_directory(dir_path: str) -> List[str]:
    """Scan a directory and return subdirectory names (LRU cached)."""
    if dir_path in _dir_cache:
        return _dir_cache[dir_path]

    try:
        entries = os.scandir(dir_path)
        subdirs = sorted(e.name for e in entries if e.is_dir() and not e.name.startswith('.'))
    except (OSError, PermissionError):
        subdirs = []

    if len(_dir_cache) >= _CACHE_SIZE:
        oldest = next(iter(_dir_cache))
        del _dir_cache[oldest]
    _dir_cache[dir_path] = subdirs
    return subdirs


scanDirectory = scan_directory


async def get_directory_completions(
    partial_path: str,
    options: Optional[CompletionOptions] = None,
) -> List[Dict[str, Any]]:
    """Return directory completion suggestions for partial_path."""
    if options is None:
        options = {}
    base = options.get('basePath') or os.getcwd()
    parsed = parse_partial_path(partial_path, base)
    subdirs = await scan_directory(parsed['dir'])
    prefix = parsed['prefix'].lower()
    matches = [d for d in subdirs if d.lower().startswith(prefix)]
    return [
        {
            'value': os.path.join(parsed['dir'], d) + os.sep,
            'label': d + os.sep,
            'type': 'directory',
        }
        for d in matches
    ]


getDirectoryCompletions = get_directory_completions


def clear_directory_cache() -> None:
    """Clear the directory cache."""
    _dir_cache.clear()


clearDirectoryCache = clear_directory_cache


def is_path_like_token(token: str) -> bool:
    """Return True if a string looks like a file path."""
    return token.startswith(('./', '../', '/', '~')) or os.sep in token


isPathLikeToken = is_path_like_token


async def scan_directory_for_paths(
    dir_path: str,
    include_hidden: bool = False,
) -> List[PathEntry]:
    """Scan a directory and return both files and subdirectories (LRU cached)."""
    cache_key = f"{dir_path}:{'h' if include_hidden else 'v'}"
    if cache_key in _path_cache:
        return _path_cache[cache_key]

    try:
        entries_list = []
        with os.scandir(dir_path) as entries:
            for e in entries:
                if not include_hidden and e.name.startswith('.'):
                    continue
                try:
                    is_dir = e.is_dir()
                except OSError:
                    is_dir = False
                entries_list.append({
                    'name': e.name,
                    'type': 'directory' if is_dir else 'file',
                    'path': e.path,
                })
        entries_list.sort(key=lambda x: (x['type'] != 'directory', x['name'].lower()))
    except (OSError, PermissionError):
        entries_list = []

    if len(_path_cache) >= _CACHE_SIZE:
        oldest = next(iter(_path_cache))
        del _path_cache[oldest]
    _path_cache[cache_key] = entries_list
    return entries_list


scanDirectoryForPaths = scan_directory_for_paths


async def get_path_completions(
    partial_path: str,
    options: Optional[CompletionOptions] = None,
) -> List[Dict[str, Any]]:
    """Return path completion suggestions including files and directories."""
    if options is None:
        options = {}
    base = options.get('basePath') or os.getcwd()
    include_hidden = options.get('includeHidden', False)
    parsed = parse_partial_path(partial_path, base)
    all_entries = await scan_directory_for_paths(parsed['dir'], include_hidden)
    prefix = parsed['prefix'].lower()
    matches = [e for e in all_entries if e['name'].lower().startswith(prefix)]
    return [
        {
            'value': e['path'] + (os.sep if e['type'] == 'directory' else ''),
            'label': e['name'] + (os.sep if e['type'] == 'directory' else ''),
            'type': e['type'],
        }
        for e in matches
    ]


getPathCompletions = get_path_completions


def clear_path_cache() -> None:
    """Clear both directory and path caches."""
    _dir_cache.clear()
    _path_cache.clear()


clearPathCache = clear_path_cache

