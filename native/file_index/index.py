"""Fuzzy file-path search index — mirrors src/native-ts/file-index/index.ts.

Provides a fast in-process fuzzy file finder used by the path-completion and
file-picker features.  Implements the same scoring algorithm as the TypeScript
original: bitmap reject, fused indexOf scan with gap/consecutive terms,
boundary/camelCase bonus pass, test-file penalty, top-k maintenance.

Public API:
    CHUNK_MS: int                                  # ms per async chunk
    yieldToEventLoop() -> Coroutine                # sleep 0 between chunks
    class FileIndex:
        loadFromFileList(fileList)                  # sync build
        loadFromFileListAsync(fileList) -> { queryable, done }  # async build
        search(query, limit) -> list[SearchResult]  # fuzzy search
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Optional

# ─── Scoring constants (identical to TS) ─────────────────────────────────────

SCORE_MATCH       = 16
BONUS_BOUNDARY    = 8
BONUS_CAMEL       = 6
BONUS_CONSECUTIVE = 4
BONUS_FIRST_CHAR  = 8
PENALTY_GAP_START = 3
PENALTY_GAP_EXTENSION = 1

TOP_LEVEL_CACHE_LIMIT = 100
MAX_QUERY_LEN = 64
CHUNK_MS = 4


@dataclass
class SearchResult:
    path: str
    score: float


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _isBoundary(ch: str) -> bool:
    return ch in "/\\._- \t"

def _isLower(ch: str) -> bool:
    return ch.islower()

def _isUpper(ch: str) -> bool:
    return ch.isupper()

def _scoreBonusAt(path: str, pos: int, first: bool) -> int:
    """Compute bonus for a match at position pos in path."""
    bonus = 0
    if first:
        bonus += BONUS_FIRST_CHAR
    if pos > 0:
        prev = path[pos - 1]
        curr = path[pos]
        if _isBoundary(prev):
            bonus += BONUS_BOUNDARY
        elif _isLower(prev) and _isUpper(curr):
            bonus += BONUS_CAMEL
    return bonus

def _computeTopLevelEntries(paths: list[str], limit: int) -> list[str]:
    """Return the first `limit` unique top-level path components."""
    seen: set[str] = set()
    result: list[str] = []
    for p in paths:
        parts = p.replace("\\", "/").split("/")
        top = parts[0] if parts else ""
        if top and top not in seen:
            seen.add(top)
            result.append(top)
            if len(result) >= limit:
                break
    return result


async def yieldToEventLoop() -> None:
    """Yield control to the event loop briefly (between index build chunks)."""
    await asyncio.sleep(0)


# ─── FileIndex ────────────────────────────────────────────────────────────────

class FileIndex:
    """In-process fuzzy file-path index."""

    def __init__(self) -> None:
        self._paths: list[str] = []
        self._lowerPaths: list[str] = []
        # charBits[i]: bitmask of which chars (a-z) appear in paths[i]
        self._charBits: list[int] = []
        self._topLevelCache: list[str] = []
        self._readyCount: int = 0

    def loadFromFileList(self, fileList: list[str]) -> None:
        """Build the index synchronously from a list of file paths."""
        # Deduplicate while preserving order
        seen: set[str] = set()
        unique: list[str] = []
        for p in fileList:
            if p not in seen:
                seen.add(p)
                unique.append(p)
        self._buildIndex(unique)

    def loadFromFileListAsync(
        self, fileList: list[str]
    ) -> dict[str, "asyncio.Future[None]"]:
        """Build the index asynchronously in CHUNK_MS-sized chunks.

        Returns {"queryable": future, "done": future}.
        "queryable" resolves when the first chunk is indexed (search is live).
        "done" resolves when the full list is indexed.
        """
        loop = asyncio.get_event_loop()
        queryable_future: "asyncio.Future[None]" = loop.create_future()
        done_future:      "asyncio.Future[None]" = loop.create_future()

        seen: set[str] = set()
        unique: list[str] = []
        for p in fileList:
            if p not in seen:
                seen.add(p)
                unique.append(p)

        async def _build() -> None:
            chunk_start = time.monotonic()
            first_chunk = True
            batch: list[str] = []
            for p in unique:
                batch.append(p)
                elapsed_ms = (time.monotonic() - chunk_start) * 1000
                if elapsed_ms >= CHUNK_MS:
                    self._appendToIndex(batch)
                    batch = []
                    if first_chunk and not queryable_future.done():
                        queryable_future.set_result(None)
                    first_chunk = False
                    await yieldToEventLoop()
                    chunk_start = time.monotonic()
            if batch:
                self._appendToIndex(batch)
            if not queryable_future.done():
                queryable_future.set_result(None)
            if not done_future.done():
                done_future.set_result(None)

        asyncio.ensure_future(_build())
        return {"queryable": queryable_future, "done": done_future}

    def _buildIndex(self, paths: list[str]) -> None:
        self._paths = list(paths)
        self._lowerPaths = [p.lower() for p in paths]
        self._charBits = [_charBitsOf(lp) for lp in self._lowerPaths]
        self._topLevelCache = _computeTopLevelEntries(paths, TOP_LEVEL_CACHE_LIMIT)
        self._readyCount = len(paths)

    def _appendToIndex(self, batch: list[str]) -> None:
        for p in batch:
            lp = p.lower()
            self._paths.append(p)
            self._lowerPaths.append(lp)
            self._charBits.append(_charBitsOf(lp))
        self._readyCount = len(self._paths)
        # Recompute top-level cache
        self._topLevelCache = _computeTopLevelEntries(self._paths, TOP_LEVEL_CACHE_LIMIT)

    def search(self, query: str, limit: int) -> list[SearchResult]:
        """Return up to `limit` results sorted by descending score."""
        if not query or not self._paths:
            return []

        q = query[:MAX_QUERY_LEN].lower()
        query_bits = _charBitsOf(q)

        # Top-k heap: list of (score, path) sorted ascending by score
        top_k: list[tuple[float, str]] = []
        threshold = float("-inf")

        for i, lp in enumerate(self._lowerPaths):
            # Bitmap reject: if any query char missing from path, skip
            if (query_bits & self._charBits[i]) != query_bits:
                continue

            score = _fuzzyScore(q, lp, self._paths[i])
            if score <= 0:
                continue

            # Test-file penalty: 5% cap at 1.0
            if "test" in lp:
                score = min(score, score / 1.05)

            if len(top_k) < limit:
                top_k.append((score, self._paths[i]))
                top_k.sort(key=lambda x: x[0])
                if len(top_k) == limit:
                    threshold = top_k[0][0]
            elif score > threshold:
                top_k[0] = (score, self._paths[i])
                top_k.sort(key=lambda x: x[0])
                threshold = top_k[0][0]

        top_k.sort(key=lambda x: x[0], reverse=True)
        return [SearchResult(path=p, score=s) for s, p in top_k]


# ─── Scoring ──────────────────────────────────────────────────────────────────

def _charBitsOf(s: str) -> int:
    """Build a 26-bit mask of which lowercase letters appear in s."""
    bits = 0
    for ch in s:
        if "a" <= ch <= "z":
            bits |= 1 << (ord(ch) - ord("a"))
    return bits


def _fuzzyScore(query: str, lower_path: str, orig_path: str) -> float:
    """Score a query against a lower-cased path. Returns 0 if no match."""
    if not query:
        return 0.0

    # Must contain all query chars in order (indexOf scan)
    pos = 0
    positions: list[int] = []
    gap_count = 0
    last_pos = -1
    for ch in query:
        idx = lower_path.find(ch, pos)
        if idx < 0:
            return 0.0
        positions.append(idx)
        if last_pos >= 0 and idx > last_pos + 1:
            gap_count += 1
        last_pos = idx
        pos = idx + 1

    if not positions:
        return 0.0

    # Base score
    score = float(SCORE_MATCH * len(positions))

    # Gap penalty
    score -= gap_count * PENALTY_GAP_START

    # Boundary / camelCase / consecutive bonuses
    first = True
    prev_pos = -2
    for i, p in enumerate(positions):
        score += _scoreBonusAt(orig_path, p, first and p == 0)
        if i > 0 and p == prev_pos + 1:
            score += BONUS_CONSECUTIVE
        first = False
        prev_pos = p

    # Prefer matches closer to the end of the path (filename > directory)
    if positions:
        last = positions[-1]
        total = len(lower_path)
        score += SCORE_MATCH * (last / total)

    return score


# ─── Exports ──────────────────────────────────────────────────────────────────

FileIndexType = FileIndex

__all__ = [
    "FileIndex",
    "FileIndexType",
    "SearchResult",
    "yieldToEventLoop",
    "CHUNK_MS",
]
