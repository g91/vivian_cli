"""Microcompact state — mirrors src/services/compact/microCompact.ts (partial)."""
from __future__ import annotations

_microcompact_state: dict = {}


def resetMicrocompactState() -> None:
    """Reset microcompact tracking state.

    Mirrors resetMicrocompactState() from microCompact.ts.
    """
    _microcompact_state.clear()


reset_microcompact_state = resetMicrocompactState
