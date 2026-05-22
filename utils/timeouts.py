"""Timeout constants — mirrors src/utils/timeouts.ts"""
from __future__ import annotations

import os

DEFAULT_TIMEOUT_MS = 120_000  # 2 minutes
MAX_TIMEOUT_MS = 600_000      # 10 minutes


def get_default_bash_timeout_ms(env: dict | None = None) -> int:
    """Return the default bash operation timeout in milliseconds."""
    _env = env if env is not None else os.environ
    raw = _env.get("BASH_DEFAULT_TIMEOUT_MS")
    if raw:
        try:
            val = int(raw)
            if val > 0:
                return val
        except ValueError:
            pass
    return DEFAULT_TIMEOUT_MS


def get_max_bash_timeout_ms(env: dict | None = None) -> int:
    """Return the maximum bash operation timeout in milliseconds."""
    _env = env if env is not None else os.environ
    default = get_default_bash_timeout_ms(_env)
    raw = _env.get("BASH_MAX_TIMEOUT_MS")
    if raw:
        try:
            val = int(raw)
            if val > 0:
                return max(val, default)
        except ValueError:
            pass
    return max(MAX_TIMEOUT_MS, default)
