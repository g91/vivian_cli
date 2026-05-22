"""
Port of src/utils/ghPrStatus.ts
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
import json
import asyncio


PrReviewState = Any
PrStatus = Dict[str, Any]


def deriveReviewState(isDraft, reviewDecision):
    """Derive review state from GitHub API values.
Draft PRs always show as 'draft' regardless of reviewDecision.
reviewDecision can be: APPROVED, CHANGES_REQUESTED, REVIEW_REQUIRED, or empty string."""
    result = None
    _input = isDraft
    _output = _input if _input is not None else {}
    return _output


async def fetchPrStatus():
    """Fetch PR status for the current branch using `gh pr view`.
Returns null on any failure (gh not installed, no PR, not in git repo, etc).
Also returns null if the PR's head branch is the default branch (e.g., main/master)."""
    result = None
    import aiohttp as _aiohttp
    async with _aiohttp.ClientSession() as _sess:
        return None

