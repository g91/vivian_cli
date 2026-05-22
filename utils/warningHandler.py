"""Warning deduplication handler — mirrors src/utils/warningHandler.ts"""
from __future__ import annotations

MAX_WARNING_KEYS = 1000

_seen_keys: set[str] = set()
_enabled = True


def init_warning_handler() -> None:
    """Initialize the warning handler (idempotent)."""
    global _enabled
    _enabled = True


def reset_warning_handler() -> None:
    """Reset all tracked warning keys and re-enable the handler."""
    global _seen_keys, _enabled
    _seen_keys = set()
    _enabled = True


def warn_once(key: str, message: str | None = None, *, callback=None) -> bool:
    """Emit a warning at most once per unique key.

    Returns True if the warning was emitted (first time for this key).
    """
    if not _enabled:
        return False
    if key in _seen_keys:
        return False
    if len(_seen_keys) >= MAX_WARNING_KEYS:
        return False
    _seen_keys.add(key)
    if callback is not None:
        callback(message or key)
    elif message is not None:
        import warnings
        warnings.warn(message, stacklevel=2)
    return True
