"""release-notes command — mirrors src/commands/release-notes/release-notes.ts."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


def _format_release_notes(notes: list[tuple[str, list[str]]]) -> str:
    return "\n\n".join(
        f"Version {version}:\n" + "\n".join(f"· {note}" for note in version_notes)
        for version, version_notes in notes
    )


async def call(args: str, context: CommandContext) -> TextResult:
    from ...types.command import TextResult
    from ...utils.releaseNotes import CHANGELOG_URL, fetchAndStoreChangelog, getAllReleaseNotes, getStoredChangelog

    fresh_notes: list[tuple[str, list[str]]] = []

    try:
        await asyncio.wait_for(fetchAndStoreChangelog(), timeout=0.5)
        fresh_notes = getAllReleaseNotes(await getStoredChangelog())
    except Exception:
        pass

    if fresh_notes:
        return TextResult(_format_release_notes(fresh_notes))

    cached_notes = getAllReleaseNotes(await getStoredChangelog())
    if cached_notes:
        return TextResult(_format_release_notes(cached_notes))

    return TextResult(f"See the full changelog at: {CHANGELOG_URL}")

