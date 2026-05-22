"""Working directory helpers — mirrors src/utils/cwd.ts"""
from __future__ import annotations

import contextvars
import os

_cwd_override: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "cwd_override", default=None
)

_original_cwd: str = os.getcwd()
_current_cwd: str = _original_cwd


def set_cwd(cwd: str) -> None:
    """Set the global current working directory."""
    global _current_cwd
    _current_cwd = cwd


def get_original_cwd() -> str:
    """Return the cwd at process startup."""
    return _original_cwd


def run_with_cwd_override(cwd: str, fn):
    """Run fn with the working directory overridden for this async context."""
    token = _cwd_override.set(cwd)
    try:
        return fn()
    finally:
        _cwd_override.reset(token)


def pwd() -> str:
    """Return the current working directory for this async context."""
    return _cwd_override.get() or _current_cwd


def get_cwd() -> str:
    """Return cwd, falling back to original cwd on error."""
    try:
        return pwd()
    except Exception:
        return _original_cwd


def setCwd(cwd: str) -> None:
    set_cwd(cwd)


def getOriginalCwd() -> str:
    return get_original_cwd()


def runWithCwdOverride(cwd: str, fn):
    return run_with_cwd_override(cwd, fn)


def getCwd() -> str:
    return get_cwd()
