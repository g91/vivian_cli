"""Team memory path helpers — mirrors src/memdir/teamMemPaths.ts."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from ..services.analytics.growthbook import getFeatureValue_CACHED_MAY_BE_STALE
from .paths import get_memory_dir, is_auto_memory_enabled


def is_team_memory_enabled() -> bool:
    if not is_auto_memory_enabled():
        return False
    return bool(getFeatureValue_CACHED_MAY_BE_STALE('tengu_herring_clock', False))


def get_team_memory_dir() -> Optional[str]:
    """Return the team memory directory when the feature is enabled."""
    if not is_team_memory_enabled():
        return None
    return str((Path(get_memory_dir()) / 'team').resolve(strict=False)) + os.sep


def is_team_mem_path(file_path: str) -> bool:
    team_dir = get_team_memory_dir()
    if not team_dir:
        return False
    resolved_path = str(Path(file_path).expanduser().resolve(strict=False))
    resolved_team_dir = str(Path(team_dir).resolve(strict=False))
    return resolved_path == resolved_team_dir or resolved_path.startswith(resolved_team_dir + os.sep)


def is_team_mem_file(file_path: str) -> bool:
    return is_team_memory_enabled() and is_team_mem_path(file_path)


isTeamMemoryEnabled = is_team_memory_enabled
getTeamMemoryDir = get_team_memory_dir
isTeamMemPath = is_team_mem_path
isTeamMemFile = is_team_mem_file
