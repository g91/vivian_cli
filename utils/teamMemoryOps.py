"""
Port of src/utils/teamMemoryOps.ts
"""
from __future__ import annotations

from typing import Any

from ..constants.tools import FILE_EDIT_TOOL_NAME, FILE_WRITE_TOOL_NAME
from ..memdir.team_mem_paths import is_team_mem_file


isTeamMemFile = is_team_mem_file


def isTeamMemorySearch(toolInput: Any) -> bool:
    """Check if a search tool use targets team memory files by examining its path."""
    if not isinstance(toolInput, dict):
        return False
    path = toolInput.get('path')
    return isinstance(path, str) and is_team_mem_file(path)


def isTeamMemoryWriteOrEdit(toolName: str, toolInput: Any) -> bool:
    """Check if a Write or Edit tool use targets a team memory file."""
    if toolName not in (FILE_WRITE_TOOL_NAME, FILE_EDIT_TOOL_NAME):
        return False
    if not isinstance(toolInput, dict):
        return False
    file_path = toolInput.get('file_path') or toolInput.get('path')
    return isinstance(file_path, str) and is_team_mem_file(file_path)


def appendTeamMemorySummaryParts(memoryCounts: dict[str, Any], isActive: bool, parts: list[str]) -> None:
    """Append team memory summary parts to the parts array."""
    team_read_count = int(memoryCounts.get('teamMemoryReadCount', 0) or 0)
    team_search_count = int(memoryCounts.get('teamMemorySearchCount', 0) or 0)
    team_write_count = int(memoryCounts.get('teamMemoryWriteCount', 0) or 0)

    if team_read_count > 0:
        verb = 'Recalling' if isActive and len(parts) == 0 else 'recalling' if isActive else 'Recalled' if len(parts) == 0 else 'recalled'
        noun = 'memory' if team_read_count == 1 else 'memories'
        parts.append(f'{verb} {team_read_count} team {noun}')

    if team_search_count > 0:
        verb = 'Searching' if isActive and len(parts) == 0 else 'searching' if isActive else 'Searched' if len(parts) == 0 else 'searched'
        parts.append(f'{verb} team memories')

    if team_write_count > 0:
        verb = 'Writing' if isActive and len(parts) == 0 else 'writing' if isActive else 'Wrote' if len(parts) == 0 else 'wrote'
        noun = 'memory' if team_write_count == 1 else 'memories'
        parts.append(f'{verb} {team_write_count} team {noun}')


is_team_memory_search = isTeamMemorySearch
is_team_memory_write_or_edit = isTeamMemoryWriteOrEdit
append_team_memory_summary_parts = appendTeamMemorySummaryParts

