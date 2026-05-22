"""Port of src/utils/swarm/reconnection.ts."""
from __future__ import annotations

from typing import Any

from ..debug import logForDebugging, logError
from ..teammate import getDynamicTeamContext
from .teamHelpers import getTeamFilePath, readTeamFile


def computeInitialTeamContext():
    """Compute initial teamContext for AppState from dynamic teammate context."""
    context = getDynamicTeamContext()

    if not isinstance(context, dict) or not context.get("teamName") or not context.get("agentName"):
        logForDebugging(
            "[Reconnection] computeInitialTeamContext: No teammate context set (not a teammate)"
        )
        return None

    team_name = context.get("teamName")
    agent_id = context.get("agentId")
    agent_name = context.get("agentName")

    team_file = readTeamFile(team_name)
    if not isinstance(team_file, dict):
        logError(f"[computeInitialTeamContext] Could not read team file for {team_name}")
        return None

    team_file_path = getTeamFilePath(team_name)
    is_leader = not agent_id

    logForDebugging(
        f"[Reconnection] Computed initial team context for {'leader' if is_leader else f'teammate {agent_name}'} in team {team_name}"
    )

    return {
        "teamName": team_name,
        "teamFilePath": team_file_path,
        "leadAgentId": team_file.get("leadAgentId"),
        "selfAgentId": agent_id,
        "selfAgentName": agent_name,
        "isLeader": is_leader,
        "teammates": {},
    }


def initializeTeammateContextFromSession(setAppState, teamName, agentName):
    """Restore teamContext in AppState for a resumed teammate session."""
    team_file = readTeamFile(teamName)
    if not isinstance(team_file, dict):
        logError(
            f"[initializeTeammateContextFromSession] Could not read team file for {teamName} (agent: {agentName})"
        )
        return None

    member = None
    for item in team_file.get("members", []) or []:
        if isinstance(item, dict) and item.get("name") == agentName:
            member = item
            break
    if member is None:
        logForDebugging(
            f"[Reconnection] Member {agentName} not found in team {teamName} - may have been removed"
        )

    agent_id = member.get("agentId") if isinstance(member, dict) else None
    team_file_path = getTeamFilePath(teamName)

    def _update(prev: Any) -> Any:
        next_context = {
            "teamName": teamName,
            "teamFilePath": team_file_path,
            "leadAgentId": team_file.get("leadAgentId"),
            "selfAgentId": agent_id,
            "selfAgentName": agentName,
            "isLeader": False,
            "teammates": {},
        }
        if isinstance(prev, dict):
            return {**prev, "teamContext": next_context}
        try:
            from copy import copy

            cloned = copy(prev)
            setattr(cloned, "teamContext", next_context)
            return cloned
        except Exception:
            return prev

    setAppState(_update)

    logForDebugging(
        f"[Reconnection] Initialized agent context from session for {agentName} in team {teamName}"
    )
    return None


compute_initial_team_context = computeInitialTeamContext
initialize_teammate_context_from_session = initializeTeammateContextFromSession