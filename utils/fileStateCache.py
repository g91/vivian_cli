"""
passpass of src/utils/fileStateCache
"""
from __future__ import annotations

from collections import OrderedDict
import os
from typing import Any, Dict, Iterable


FileState = Dict[str, Any]

READ_FILE_STATE_CACHE_SIZE = 100
DEFAULT_MAX_CACHE_SIZE_BYTES = 25 * 1024 * 1024


def _normalize_key(key: str) -> str:
    return os.path.normpath(key)


def _size_of(value: FileState) -> int:
    content = value.get("content", "")
    if isinstance(content, bytes):
        return max(1, len(content))
    return max(1, len(str(content).encode("utf-8")))


class FileStateCache:
    """A file state cache that normalizes all path keys before access.
This ensures consistent cache hits regardless of whether callers pass
relative vs absolute paths with redundant segments (e.g. /foo/../bar)
or mixed path separators on Windows (/ vs \\)."""

    def __init__(self, maxEntries: int, maxSizeBytes: int):
        self._cache: OrderedDict[str, FileState] = OrderedDict()
        self._sizes: dict[str, int] = {}
        self._calculated_size = 0
        self._max = maxEntries
        self._max_size = maxSizeBytes

    def get(self, key: str):
        normalized = _normalize_key(key)
        value = self._cache.get(normalized)
        if value is None:
            return None
        self._cache.move_to_end(normalized)
        return value

    def set(self, key: str, value: FileState):
        normalized = _normalize_key(key)
        if normalized in self._cache:
            self._calculated_size -= self._sizes.get(normalized, 0)
            del self._cache[normalized]
        size = _size_of(value)
        self._cache[normalized] = value
        self._sizes[normalized] = size
        self._calculated_size += size
        self._cache.move_to_end(normalized)
        self._evict_if_needed()
        return self

    def has(self, key: str) -> bool:
        return _normalize_key(key) in self._cache

    def delete(self, key: str) -> bool:
        normalized = _normalize_key(key)
        if normalized not in self._cache:
            return False
        self._calculated_size -= self._sizes.pop(normalized, 0)
        del self._cache[normalized]
        return True

    def clear(self) -> None:
        self._cache.clear()
        self._sizes.clear()
        self._calculated_size = 0

    @property
    def size(self) -> int:
        return len(self._cache)

    @property
    def max(self) -> int:
        return self._max

    @property
    def maxSize(self) -> int:
        return self._max_size

    @property
    def calculatedSize(self) -> int:
        return self._calculated_size

    def keys(self):
        for key in self._cache.keys():
            yield key

    def entries(self):
        for item in self._cache.items():
            yield item

    def dump(self):
        return [
            {"key": key, "value": value}
            for key, value in self._cache.items()
        ]

    def load(self, entries):
        self.clear()
        for entry in entries or []:
            if isinstance(entry, dict) and "key" in entry and "value" in entry:
                self.set(entry["key"], entry["value"])

    def _evict_if_needed(self) -> None:
        while self._cache and (
            len(self._cache) > self._max or self._calculated_size > self._max_size
        ):
            oldest_key, _ = self._cache.popitem(last=False)
            self._calculated_size -= self._sizes.pop(oldest_key, 0)


def createFileStateCacheWithSizeLimit(maxEntries, maxSizeBytes=DEFAULT_MAX_CACHE_SIZE_BYTES):
    """Factory function to create a size-limited FileStateCache."""
    return FileStateCache(maxEntries, maxSizeBytes)


def cacheToObject(cache):
    return dict(cache.entries())


def cacheKeys(cache):
    return list(cache.keys())


def cloneFileStateCache(cache):
    cloned = createFileStateCacheWithSizeLimit(cache.max, cache.maxSize)
    cloned.load(cache.dump())
    return cloned


def mergeFileStateCaches(first, second):
    merged = cloneFileStateCache(first)
    for filePath, fileState in second.entries():
        existing = merged.get(filePath)
        if not existing or fileState.get("timestamp", 0) > existing.get("timestamp", 0):
            merged.set(filePath, fileState)
    return merged


create_file_state_cache_with_size_limit = createFileStateCacheWithSizeLimit
cache_to_object = cacheToObject
cache_keys = cacheKeys
clone_file_state_cache = cloneFileStateCache
merge_file_state_caches = mergeFileStateCaches
