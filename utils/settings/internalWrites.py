"""Port of src/utils/settings/internalWrites.ts"""
from __future__ import annotations
import time
from typing import Dict

_timestamps: Dict[str, float] = {}


def markInternalWrite(path: str) -> None:
    """Mark that vivian Code is about to write to the given settings file path."""
    _timestamps[path] = time.time() * 1000  # ms


def consumeInternalWrite(path: str, window_ms: float) -> bool:
    """Return True if path was marked as an internal write within window_ms milliseconds.
    Consumes the mark on match so subsequent changes are not suppressed."""
    ts = _timestamps.get(path)
    if ts is not None and (time.time() * 1000 - ts) < window_ms:
        del _timestamps[path]
        return True
    return False


def clearInternalWrites() -> None:
    """Clear all recorded internal write timestamps."""
    _timestamps.clear()
