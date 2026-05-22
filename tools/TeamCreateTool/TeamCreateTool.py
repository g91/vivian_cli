"""TeamCreateTool — mirrors src/tools/TeamCreateTool/TeamCreateTool.tsx"""
from __future__ import annotations
import time
from typing import Any, Dict

from ...bootstrap.state import getSessionId
from ...utils.model.model import getDefaultMainLoopModel, parseUserSpecifiedModel
from ...utils.swarm.constants import TEAM_LEAD_NAME
from ...utils.swarm.teamHelpers import (
    getTeamFilePath,
    readTeamFile,
    registerTeamForSessionCleanup,
    sanitizeName,
    writeTeamFileAsync,
)
from ...utils.swarm.teammateLayoutManager import assignTeammateColor
from ...utils.tasks import ensureTasksDir, resetTaskList, setLeaderTeamName

TOOL_NAME = 'TeamCreate'

INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "team_name": {"type": "string"},
        "name": {"type": "string"},
        "description": {"type": "string"},
        "agent_type": {"type": "string"},
    },
}


async def description() -> str:
    return 'Create a new agent team.'


async def prompt() -> str:
    return 'Use this tool to create a team of agents for a multi-agent workflow.'


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


def _lead_agent_id(team_name: str) -> str:
    return f"{TEAM_LEAD_NAME}@{sanitizeName(team_name)}"


async def call(input_data: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    team_name = str(input_data.get('team_name') or input_data.get('name') or '').strip()
    if not team_name:
        return {"success": False, "message": "team_name is required for TeamCreate"}

    app_state = _get_app_state(context)
    existing_team = ((app_state.get('teamContext') or {}) if isinstance(app_state, dict) else {}).get('teamName')
    if existing_team:
        return {
            "success": False,
            "message": f'Already leading team "{existing_team}". Delete the current team before creating a new one.',
        }

    final_team_name = team_name
    if readTeamFile(final_team_name):
        suffix = 2
        while readTeamFile(f"{team_name}-{suffix}"):
            suffix += 1
        final_team_name = f"{team_name}-{suffix}"

    lead_agent_id = _lead_agent_id(final_team_name)
    lead_agent_type = input_data.get('agent_type') or TEAM_LEAD_NAME
    main_model = parseUserSpecifiedModel((_get_app_state(context).get('mainLoopModel') if isinstance(_get_app_state(context), dict) else None) or getDefaultMainLoopModel())
    now = int(time.time() * 1000)
    team_file_path = getTeamFilePath(final_team_name)
    team_file = {
        'name': final_team_name,
        'description': input_data.get('description'),
        'createdAt': now,
        'leadAgentId': lead_agent_id,
        'leadSessionId': getSessionId(),
        'members': [
            {
                'agentId': lead_agent_id,
                'name': TEAM_LEAD_NAME,
                'agentType': lead_agent_type,
                'model': main_model,
                'joinedAt': now,
                'tmuxPaneId': '',
                'cwd': context.get('cwd') if isinstance(context, dict) and context.get('cwd') else __import__('os').getcwd(),
                'subscriptions': [],
                'color': assignTeammateColor(lead_agent_id),
            }
        ],
    }

    await writeTeamFileAsync(final_team_name, team_file)
    registerTeamForSessionCleanup(final_team_name)

    task_list_id = sanitizeName(final_team_name)
    await resetTaskList(task_list_id)
    await ensureTasksDir(task_list_id)
    setLeaderTeamName(task_list_id)

    _set_app_state(
        context,
        lambda prev: {
            **(prev or {}),
            'teamContext': {
                'teamName': final_team_name,
                'teamFilePath': team_file_path,
                'leadAgentId': lead_agent_id,
                'teammates': {
                    lead_agent_id: {
                        'name': TEAM_LEAD_NAME,
                        'agentType': lead_agent_type,
                        'color': team_file['members'][0]['color'],
                        'tmuxSessionName': '',
                        'tmuxPaneId': '',
                        'cwd': team_file['members'][0]['cwd'],
                        'spawnedAt': now,
                    }
                },
            },
        },
    )

    return {
        'team_name': final_team_name,
        'team_file_path': team_file_path,
        'lead_agent_id': lead_agent_id,
    }
