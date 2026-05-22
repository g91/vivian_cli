"""Port of src/bridge/sessionIdCompat.ts

Session ID tag translation helpers for the CCR v2 compat layer.
"""
from __future__ import annotations

from typing import Callable, Optional


_is_cse_shim_enabled: Optional[Callable[[], bool]] = None


def setCseShimGate(gate: Callable[[], bool]) -> None:
    """Register the GrowthBook gate for the cse_ shim."""
    global _is_cse_shim_enabled
    _is_cse_shim_enabled = gate


def toCompatSessionId(id_: str) -> str:
    """Re-tag a `cse_*` session ID to `session_*` for use with v1 compat API."""
    if not id_.startswith("cse_"):
        return id_
    if _is_cse_shim_enabled is not None and not _is_cse_shim_enabled():
        return id_
    return "session_" + id_[len("cse_"):]


def toInfraSessionId(id_: str) -> str:
    """Re-tag a `session_*` session ID to `cse_*` for infrastructure-layer calls."""
    if not id_.startswith("session_"):
        return id_
    return "cse_" + id_[len("session_"):]
