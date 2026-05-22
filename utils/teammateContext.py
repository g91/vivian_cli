"""Port of src/utils/teammateContext.ts."""
from __future__ import annotations

from contextvars import ContextVar
from typing import Any


TeammateContext = dict[str, Any]

_teammate_context_storage: ContextVar[TeammateContext | None] = ContextVar(
    "teammate_context_storage",
    default=None,
)


def getTeammateContext() -> TeammateContext | None:
    """Get the current in-process teammate context, if any."""
    return _teammate_context_storage.get()


def runWithTeammateContext(context: TeammateContext, fn=None):
    """Run a function with teammate context set."""
    token = _teammate_context_storage.set(context)
    try:
        return fn() if callable(fn) else None
    finally:
        _teammate_context_storage.reset(token)


def isInProcessTeammate() -> bool:
    """Check if current execution is within an in-process teammate."""
    return _teammate_context_storage.get() is not None


def createTeammateContext(config=None) -> TeammateContext:
    """Create a TeammateContext from spawn configuration."""
    config = dict(config or {})
    return {
        **config,
        "isInProcess": True,
    }


get_teammate_context = getTeammateContext
run_with_teammate_context = runWithTeammateContext
is_in_process_teammate = isInProcessTeammate
create_teammate_context = createTeammateContext
