"""
Port of src/utils/plugins/gitAvailability.ts

Utility for checking git availability.
"""
from __future__ import annotations

import shutil
from functools import lru_cache


async def _is_command_available(command: str) -> bool:
    """Check if a command is available in PATH."""
    return shutil.which(command) is not None


@lru_cache(maxsize=1)
def _check_git_available_cached() -> bool:
    """Cached sync check."""
    return shutil.which("git") is not None


async def checkGitAvailable() -> bool:
    """Check if git is available on the system. Memoized per session."""
    return _check_git_available_cached()


def markGitUnavailable() -> None:
    """Force the memoized git-availability check to return False."""
    _check_git_available_cached.cache_clear()
    # Re-populate with False
    _check_git_available_cached()
    # Override the cache by clearing and using a lambda that returns False
    # Since lru_cache doesn't support set(), we use a module-level flag
    global _git_unavailable_override
    _git_unavailable_override = True


_git_unavailable_override = False


# Patch checkGitAvailable to respect the override
async def checkGitAvailable() -> bool:
    if _git_unavailable_override:
        return False
    return _check_git_available_cached()


def clearGitAvailabilityCache() -> None:
    """Clear the git availability cache."""
    global _git_unavailable_override
    _git_unavailable_override = False
    _check_git_available_cached.cache_clear()

