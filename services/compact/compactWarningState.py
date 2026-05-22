"""Compact warning state — mirrors src/services/compact/compactWarningState.ts."""
from __future__ import annotations

from ...state.store import create_store

compactWarningStore = create_store(False)


def suppressCompactWarning() -> None:
    """Suppress the compact warning. Call after successful compaction.

    Mirrors suppressCompactWarning() from compactWarningState.ts.
    """
    compactWarningStore.set_state(lambda _: True)


def clearCompactWarningSuppression() -> None:
    """Clear the compact warning suppression.

    Mirrors clearCompactWarningSuppression() from compactWarningState.ts.
    """
    compactWarningStore.set_state(lambda _: False)


suppress_compact_warning = suppressCompactWarning
clear_compact_warning_suppression = clearCompactWarningSuppression
