"""TeamDeleteTool — mirrors src/tools/TeamDeleteTool/TeamDeleteTool.tsx"""
from __future__ import annotations
from typing import Any, Dict

from ...utils.swarm.constants import TEAM_LEAD_NAME
from ...utils.swarm.teamHelpers import cleanupTeamDirectories, readTeamFile, unregisterTeamForSessionCleanup
from ...utils.swarm.teammateLayoutManager import clearTeammateColors
from ...utils.tasks import clearLeaderTeamName

TOOL_NAME = 'TeamDelete'

INPUT_SCHEMA = {
    "type": "object",
    "properties": {},
}


async def description() -> str:
    return 'Delete an agent team.'


async def prompt() -> str:
    return 'Use this tool to delete an existing agent team.'


def _get_app_state(context: Any) -> dict[str, Any]:
    if isinstance(context, dict):
        getter = context.get('getAppState')
        if callable(getter):
            state = getter()
            if isinstance(state, dict):
                return state
        state = context.get('app_state')
        if isinstance(state, dict):
            return state
    return {}


def _set_app_state(context: Any, updater) -> None:
    if isinstance(context, dict):
        setter = context.get('setAppState')
        if callable(setter):
            setter(updater)
            return
        current = context.get('app_state') if isinstance(context.get('app_state'), dict) else {}
        context['app_state'] = updater(current)


async def call(input_data: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    del input_data
    app_state = _get_app_state(context)
    team_context = app_state.get('teamContext') or {}
    team_name = team_context.get('teamName')

    if team_name:
        team_file = readTeamFile(team_name)
        if team_file:
            non_lead_members = [member for member in team_file.get('members', []) if member.get('name') != TEAM_LEAD_NAME]
            active_members = [member for member in non_lead_members if member.get('isActive') is not False]
            if active_members:
                member_names = ', '.join(str(member.get('name', 'unknown')) for member in active_members)
                return {
                    'success': False,
                    'message': f'Cannot cleanup team with {len(active_members)} active member(s): {member_names}.',
                    'team_name': team_name,
                }

        await cleanupTeamDirectories(team_name)
        unregisterTeamForSessionCleanup(team_name)
        clearTeammateColors()
        clearLeaderTeamName()

    _set_app_state(
        context,
        lambda prev: {
            **(prev or {}),
            'teamContext': None,
            'inbox': {'messages': []},
        },
    )

    return {
        'success': True,
        'message': f'Cleaned up directories and worktrees for team "{team_name}"' if team_name else 'No team name found, nothing to clean up',
        'team_name': team_name,
    }
