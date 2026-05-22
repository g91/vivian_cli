"""
Port of src/utils/teamDiscovery.ts
"""
from __future__ import annotations

from typing import Any, Dict

from .swarm.backends.types import isPaneBackend
from .swarm.teamHelpers import readTeamFile


TeamSummary = Dict[str, Any]
TeammateStatus = Dict[str, Any]


def getTeammateStatuses(teamName: str) -> list[TeammateStatus]:
    """Get detailed teammate statuses for a team
Reads isActive from config to determine status"""
    team_file = readTeamFile(teamName)
    if not team_file:
        return []

    hidden_pane_ids = set(team_file.get('hiddenPaneIds') or [])
    statuses: list[TeammateStatus] = []

    for member in team_file.get('members', []):
        if member.get('name') == 'team-lead':
            continue

        is_active = member.get('isActive') is not False
        backend_type = member.get('backendType')

        statuses.append(
            {
                'name': member.get('name'),
                'agentId': member.get('agentId'),
                'agentType': member.get('agentType'),
                'model': member.get('model'),
                'prompt': member.get('prompt'),
                'status': 'running' if is_active else 'idle',
                'color': member.get('color'),
                'tmuxPaneId': member.get('tmuxPaneId'),
                'cwd': member.get('cwd'),
                'worktreePath': member.get('worktreePath'),
                'isHidden': member.get('tmuxPaneId') in hidden_pane_ids,
                'backendType': backend_type if isPaneBackend(backend_type) else None,
                'mode': member.get('mode'),
            }
        )

    return statuses


get_teammate_statuses = getTeammateStatuses

