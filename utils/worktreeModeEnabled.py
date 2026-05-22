"""
Port of src/utils/worktreeModeEnabled.ts
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING


def isWorktreeModeEnabled():
    """Worktree mode is now unconditionally enabled for all users.

Previously gated by GrowthBook flag 'tengu_worktree_mode', but the
CACHED_MAY_BE_STALE pattern returns the default (false) on first launch
before the cache is populated, silently swallowing --worktree.
See https://github.com/anthropics/vivian-code/issues/27044."""
    return True

