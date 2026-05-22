"""Post-compact cleanup — mirrors src/services/compact/postCompactCleanup.ts."""
from __future__ import annotations

from typing import Optional


def runPostCompactCleanup(query_source: Optional[str] = None) -> None:
    """Run cleanup of caches and tracking state after compaction.

    Mirrors runPostCompactCleanup() from postCompactCleanup.ts.
    """
    is_main_thread_compact = (
        query_source is None
        or query_source.startswith("repl_main_thread")
        or query_source == "sdk"
    )

    try:
        from .microCompact import resetMicrocompactState
        resetMicrocompactState()
    except Exception:
        pass

    if is_main_thread_compact:
        try:
            from ...utils.vivianmd import resetGetMemoryFilesCache
            resetGetMemoryFilesCache("compact")
        except Exception:
            pass

    try:
        from ...constants.systemPromptSections import clearSystemPromptSections
        clearSystemPromptSections()
    except Exception:
        pass

    try:
        from ...utils.classifierApprovals import clearClassifierApprovals
        clearClassifierApprovals()
    except Exception:
        pass

    try:
        from ...utils.sessionStorage import clearSessionMessagesCache
        clearSessionMessagesCache()
    except Exception:
        pass


run_post_compact_cleanup = runPostCompactCleanup
