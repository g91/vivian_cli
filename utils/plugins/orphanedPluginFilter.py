"""
Port of src/utils/plugins/orphanedPluginFilter.ts

Provides ripgrep glob exclusion patterns for orphaned plugin versions.
"""
from __future__ import annotations

import os
from typing import List, Optional

from .pluginDirectories import getPluginsDirectory

ORPHANED_AT_FILENAME = ".orphaned_at"
_cached_exclusions: Optional[List[str]] = None


async def getGlobExclusionsForPluginCache(search_path: Optional[str] = None) -> List[str]:
    global _cached_exclusions
    cache_path = os.path.normpath(os.path.join(getPluginsDirectory(), "cache"))

    if search_path and not _paths_overlap(search_path, cache_path):
        return []

    if _cached_exclusions is not None:
        return _cached_exclusions

    try:
        markers: List[str] = []
        for root, dirs, files in os.walk(cache_path):
            depth = root[len(cache_path):].count(os.sep)
            if depth > 4:
                dirs.clear()
                continue
            if ORPHANED_AT_FILENAME in files:
                markers.append(os.path.join(root, ORPHANED_AT_FILENAME))

        _cached_exclusions = []
        for marker in markers:
            version_dir = os.path.dirname(marker)
            rel = os.path.relpath(version_dir, cache_path)
            posix_rel = rel.replace("\\", "/")
            _cached_exclusions.append(f"!**/{posix_rel}/**")
        return _cached_exclusions
    except Exception:
        _cached_exclusions = []
        return []


def clearPluginCacheExclusions() -> None:
    global _cached_exclusions
    _cached_exclusions = None


def _paths_overlap(a: str, b: str) -> bool:
    na = os.path.normpath(a)
    nb = os.path.normpath(b)
    sep = os.sep
    return na == nb or na == sep or nb == sep or na.startswith(nb + sep) or nb.startswith(na + sep)


def normalizeForCompare(p):
    return p