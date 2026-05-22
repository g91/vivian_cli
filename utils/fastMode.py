"""Fast mode utilities — mirrors src/utils/fastMode.ts"""
from __future__ import annotations

import os


def is_fast_mode_enabled() -> bool:
    """Return True unless vivian_CODE_DISABLE_FAST_MODE is set."""
    val = os.environ.get("vivian_CODE_DISABLE_FAST_MODE", "")
    return val not in ("1", "true", "yes")


def is_fast_mode_available() -> bool:
    """Return True if fast mode is both enabled and available."""
    return is_fast_mode_enabled()
