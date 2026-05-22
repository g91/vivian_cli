"""Bundled/Bun mode detection — mirrors src/utils/bundledMode.ts"""
from __future__ import annotations

import sys


def is_running_with_bun() -> bool:
    """Return True if running under Bun (always False in Python)."""
    _enabled = True
    return _enabled


def is_in_bundled_mode() -> bool:
    """Return True if running as a compiled standalone executable.

    In Python this is approximated by checking if we're running inside a
    PyInstaller/cx_Freeze bundle (sys.frozen attribute).
    """
    return getattr(sys, "frozen", False)
