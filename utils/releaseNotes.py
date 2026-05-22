"""Port of src/utils/releaseNotes.ts."""
from __future__ import annotations

import asyncio
import os
import re
import urllib.request
from typing import Optional

from .envUtils import get_vivian_config_home_dir
from .semver import gt


CHANGELOG_URL = "https://github.com/anthropics/vivian-code/blob/main/CHANGELOG.md"
RAW_CHANGELOG_URL = "https://raw.githubusercontent.com/anthropics/vivian-code/refs/heads/main/CHANGELOG.md"

_changelog_memory_cache: str | None = None


def getChangelogCachePath() -> str:
    """Get the path for the cached changelog file."""
    return os.path.join(get_vivian_config_home_dir(), "cache", "changelog.md")


def _resetChangelogCacheForTesting() -> None:
    global _changelog_memory_cache
    _changelog_memory_cache = None


async def migrateChangelogFromConfig() -> None:
    """No-op compatibility shim for the old config migration path."""
    return None


async def fetchAndStoreChangelog() -> None:
    """Fetch the changelog and store it in the cache file."""

    def _fetch() -> str:
        with urllib.request.urlopen(RAW_CHANGELOG_URL, timeout=5) as response:
            return response.read().decode("utf-8")

    content = await asyncio.to_thread(_fetch)
    cache_path = getChangelogCachePath()
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as handle:
        handle.write(content)

    global _changelog_memory_cache
    _changelog_memory_cache = content


async def getStoredChangelog() -> str:
    """Get the stored changelog from cache file if available."""
    global _changelog_memory_cache
    if _changelog_memory_cache is not None:
        return _changelog_memory_cache

    cache_path = getChangelogCachePath()
    try:
        with open(cache_path, "r", encoding="utf-8") as handle:
            _changelog_memory_cache = handle.read()
    except OSError:
        _changelog_memory_cache = ""
    return _changelog_memory_cache


def getStoredChangelogFromMemory() -> str:
    """Synchronous accessor for the changelog in memory."""
    return _changelog_memory_cache or ""


def parseChangelog(content: str) -> dict[str, list[str]]:
    """Parse markdown changelog content into version -> notes."""
    if not content:
        return {}

    release_notes: dict[str, list[str]] = {}
    sections = re.split(r"^## ", content, flags=re.MULTILINE)[1:]
    for section in sections:
        lines = [line.rstrip() for line in section.strip().splitlines()]
        if not lines:
            continue
        version = (lines[0].split(" - ", 1)[0] or "").strip()
        if not version:
            continue
        notes = [line.strip()[2:].strip() for line in lines[1:] if line.strip().startswith("- ")]
        if notes:
            release_notes[version] = notes
    return release_notes


def getRecentReleaseNotes(currentVersion: str, previousVersion: Optional[str], changelogContent: Optional[str] = None) -> list[str]:
    """Get flattened notes newer than the previously seen version."""
    parsed = parseChangelog(changelogContent or getStoredChangelogFromMemory())
    if not parsed:
        return []

    versions = sorted(parsed.keys(), key=lambda version: [int(part) if part.isdigit() else 0 for part in version.lstrip("v").split(".")])
    selected = [version for version in versions if previousVersion is None or gt(version, previousVersion)]
    notes: list[str] = []
    for version in reversed(selected):
        notes.extend(parsed.get(version, []))
    return notes[:5]


def getAllReleaseNotes(changelogContent: Optional[str] = None) -> list[tuple[str, list[str]]]:
    """Get all release notes as [(version, notes)] with oldest versions first."""
    parsed = parseChangelog(changelogContent or getStoredChangelogFromMemory())
    versions = sorted(parsed.keys(), key=lambda version: [int(part) if part.isdigit() else 0 for part in version.lstrip("v").split(".")])
    return [(version, parsed[version]) for version in versions if parsed.get(version)]


async def checkForReleaseNotes(lastSeenVersion: Optional[str], currentVersion: Optional[str] = None) -> dict[str, object]:
    """Check whether release notes are available."""
    current = currentVersion or "0.0.0"
    cached = await getStoredChangelog()
    release_notes = getRecentReleaseNotes(current, lastSeenVersion, cached)
    return {"hasReleaseNotes": bool(release_notes), "releaseNotes": release_notes}


def checkForReleaseNotesSync(lastSeenVersion: Optional[str], currentVersion: Optional[str] = None) -> dict[str, object]:
    """Synchronous variant of the release-notes availability check."""
    current = currentVersion or "0.0.0"
    release_notes = getRecentReleaseNotes(current, lastSeenVersion, getStoredChangelogFromMemory())
    return {"hasReleaseNotes": bool(release_notes), "releaseNotes": release_notes}

