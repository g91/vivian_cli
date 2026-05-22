"""File suggestion utilities mirroring src/hooks/fileSuggestions.ts.

This Python port keeps the same exported surface for cache reset, list
signatures, and file suggestion generation.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
from typing import Any, Callable


_cache_generation = 0
_cached_file_list: list[str] = []
_subscribers: list[Callable[[], None]] = []


def clearFileSuggestionCaches() -> None:
    global _cache_generation, _cached_file_list
    _cache_generation += 1
    _cached_file_list = []


def pathListSignature(paths: list[str]) -> str:
    n = len(paths)
    stride = max(1, n // 500)
    h = 0x811C9DC5

    for i in range(0, n, stride):
        p = paths[i]
        for ch in p:
            h = ((h ^ ord(ch)) * 0x01000193) & 0xFFFFFFFF
        h = (h * 0x01000193) & 0xFFFFFFFF

    if n > 0:
        last = paths[-1]
        for ch in last:
            h = ((h ^ ord(ch)) * 0x01000193) & 0xFFFFFFFF

    return f"{n}:{h:08x}"


def getDirectoryNames(paths: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for p in paths:
        d = os.path.dirname(p)
        if d and d not in seen:
            seen.add(d)
            out.append(d)
    return out


def findLongestCommonPrefix(paths: list[str]) -> str:
    if not paths:
        return ""
    prefix = paths[0]
    for p in paths[1:]:
        while prefix and not p.startswith(prefix):
            prefix = prefix[:-1]
    return prefix


def _scan_files(cwd: str) -> list[str]:
    files: list[str] = []
    for root, dirs, names in os.walk(cwd):
        dirs[:] = [d for d in dirs if d not in {".git", "node_modules", "dist", "build", "__pycache__"}]
        for name in names:
            if name.startswith("."):
                continue
            full = os.path.join(root, name)
            rel = os.path.relpath(full, cwd)
            files.append(rel)
    return files


def startBackgroundCacheRefresh(cwd: str | None = None) -> None:
    global _cached_file_list
    base = cwd or os.getcwd()
    _cached_file_list = _scan_files(base)
    for callback in list(_subscribers):
        try:
            callback()
        except Exception:
            pass


def generateFileSuggestions(
    query: str,
    showOnEmpty: bool = False,
    max_results: int = 20,
    cwd: str | None = None,
) -> list[dict[str, Any]]:
    if not query and not showOnEmpty:
        return []

    base = cwd or os.getcwd()
    file_list = _cached_file_list or _scan_files(base)
    q = query.lower().strip()

    scored: list[tuple[float, str]] = []
    for rel in file_list:
        rel_lower = rel.lower()
        if not q:
            score = 0.9
        elif q in rel_lower:
            score = max(0.0, 0.8 - (rel_lower.index(q) / max(1, len(rel_lower))))
        else:
            continue
        scored.append((score, rel))

    scored.sort(key=lambda x: x[0])
    out: list[dict[str, Any]] = []
    for score, rel in scored[:max_results]:
        out.append(
            {
                "id": f"file-{rel}",
                "displayText": rel,
                "description": os.path.dirname(rel) or ".",
                "metadata": {"score": score},
            },
        )
    return out


def applyFileSuggestion(current_input: str, suggestion: str, cursor_pos: int | None = None) -> str:
    if cursor_pos is None:
        cursor_pos = len(current_input)
    before = current_input[:cursor_pos]
    after = current_input[cursor_pos:]
    return f"{before}{suggestion}{after}"


def onIndexBuildComplete(callback: Callable[[], None]) -> Callable[[], None]:
    _subscribers.append(callback)

    def _unsubscribe() -> None:
        if callback in _subscribers:
            _subscribers.remove(callback)

    return _unsubscribe


clear_file_suggestion_caches = clearFileSuggestionCaches
path_list_signature = pathListSignature
get_directory_names = getDirectoryNames
find_longest_common_prefix = findLongestCommonPrefix
start_background_cache_refresh = startBackgroundCacheRefresh
generate_file_suggestions = generateFileSuggestions
apply_file_suggestion = applyFileSuggestion
on_index_build_complete = onIndexBuildComplete
