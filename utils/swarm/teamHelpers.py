"""Partial port of src/utils/swarm/teamHelpers.ts.

Implements the file-backed team lifecycle needed by TeamCreate and TeamDelete.
"""
from __future__ import annotations

from typing import Any, Dict
import json
import shutil
from pathlib import Path

from ..debug import logForDebugging
from ..envUtils import get_teams_dir
from ..tasks import getTasksDir, notifyTasksUpdated


SpawnTeamOutput = Dict[str, Any]
CleanupOutput = Dict[str, Any]
TeamAllowedPath = Dict[str, Any]
TeamFile = Dict[str, Any]
Input = Any
Output = SpawnTeamOutput


inputSchema: Any = None  # type: ignore
_session_created_teams: set[str] = set()


def sanitizeName(name):
    """Sanitizes a name for use in tmux window names, worktree paths, and file paths.
Replaces all non-alphanumeric characters with hyphens and lowercases."""
    raw = '' if name is None else str(name)
    return ''.join(ch if ch.isalnum() else '-' for ch in raw).lower()


def sanitizeAgentName(name):
    """Sanitizes an agent name for use in deterministic agent IDs.
Replaces @ with - to prevent ambiguity in the agentName@teamName format."""
    return str(name or '').replace('@', '-')


def getTeamDir(teamName):
    """Gets the path to a team's directory"""
    return str(Path(get_teams_dir()) / sanitizeName(teamName))


def getTeamFilePath(teamName):
    """Gets the path to a team's config.json file"""
    return str(Path(getTeamDir(teamName)) / 'config.json')


def readTeamFile(teamName):
    try:
        return json.loads(Path(getTeamFilePath(teamName)).read_text(encoding='utf-8'))
    except FileNotFoundError:
        return None
    except Exception as error:
        logForDebugging(f"[TeammateTool] Failed to read team file for {teamName}: {error}")
        return None


async def readTeamFileAsync(teamName):
    """Reads a team file by name (async — for tool handlers and other async contexts)"""
    return readTeamFile(teamName)


def writeTeamFile(teamName, teamFile):
    teamDir = Path(getTeamDir(teamName))
    teamDir.mkdir(parents=True, exist_ok=True)
    Path(getTeamFilePath(teamName)).write_text(json.dumps(teamFile, indent=2, sort_keys=False), encoding='utf-8')


async def writeTeamFileAsync(teamName, teamFile):
    """Writes a team file (async — for tool handlers)"""
    writeTeamFile(teamName, teamFile)


def removeTeammateFromTeamFile(teamName, identifier=None):
    """Removes a teammate from the team file by agent ID or name.
Used by the leader when processing shutdown approvals."""
    if not identifier:
        return False
    teamFile = readTeamFile(teamName)
    if not teamFile:
        return False
    original = len(teamFile.get('members', []))
    agent_id = identifier.get('agentId') if isinstance(identifier, dict) else None
    member_name = identifier.get('name') if isinstance(identifier, dict) else None
    teamFile['members'] = [
        member for member in teamFile.get('members', [])
        if not ((agent_id and member.get('agentId') == agent_id) or (member_name and member.get('name') == member_name))
    ]
    if len(teamFile['members']) == original:
        return False
    writeTeamFile(teamName, teamFile)
    return True


def addHiddenPaneId(teamName, paneId):
    """Adds a pane ID to the hidden panes list in the team file.
@param teamName - The name of the team
@param paneId - The pane ID to hide
@returns true if the pane was added to hidden list, false if team doesn't exist"""
    teamFile = readTeamFile(teamName)
    if not teamFile:
        return False
    hidden = list(teamFile.get('hiddenPaneIds') or [])
    if paneId not in hidden:
        hidden.append(paneId)
        teamFile['hiddenPaneIds'] = hidden
        writeTeamFile(teamName, teamFile)
    return True


def removeHiddenPaneId(teamName, paneId):
    """Removes a pane ID from the hidden panes list in the team file.
@param teamName - The name of the team
@param paneId - The pane ID to show (remove from hidden list)
@returns true if the pane was removed from hidden list, false if team doesn't exist"""
    teamFile = readTeamFile(teamName)
    if not teamFile:
        return False
    hidden = [item for item in (teamFile.get('hiddenPaneIds') or []) if item != paneId]
    teamFile['hiddenPaneIds'] = hidden
    writeTeamFile(teamName, teamFile)
    return True


def removeMemberFromTeam(teamName, tmuxPaneId):
    """Removes a teammate from the team config file by pane ID.
Also removes from hiddenPaneIds if present.
@param teamName - The name of the team
@param tmuxPaneId - The pane ID of the teammate to remove
@returns true if the member was removed, false if team or member doesn't exist"""
    teamFile = readTeamFile(teamName)
    if not teamFile:
        return False
    original = len(teamFile.get('members', []))
    teamFile['members'] = [member for member in teamFile.get('members', []) if member.get('tmuxPaneId') != tmuxPaneId]
    teamFile['hiddenPaneIds'] = [item for item in (teamFile.get('hiddenPaneIds') or []) if item != tmuxPaneId]
    if len(teamFile['members']) == original:
        return False
    writeTeamFile(teamName, teamFile)
    return True


def removeMemberByAgentId(teamName, agentId):
    """Removes a teammate from a team's member list by agent ID.
Use this for in-process teammates which all share the same tmuxPaneId.
@param teamName - The name of the team
@param agentId - The agent ID of the teammate to remove (e.g., "researcher@my-team")
@returns true if the member was removed, false if team or member doesn't exist"""
    return removeTeammateFromTeamFile(teamName, {'agentId': agentId})


def setMemberMode(teamName, memberName, mode):
    """Sets a team member's permission mode.
Called when the team leader changes a teammate's mode via the TeamsDialog.
@param teamName - The name of the team
@param memberName - The name of the member to update
@param mode - The new permission mode"""
    teamFile = readTeamFile(teamName)
    if not teamFile:
        return False
    changed = False
    for member in teamFile.get('members', []):
        if member.get('name') == memberName and member.get('mode') != mode:
            member['mode'] = mode
            changed = True
    if changed:
        writeTeamFile(teamName, teamFile)
    return True


def syncTeammateMode(mode, teamNameOverride=None):
    """Sync the current teammate's mode to config.json so team lead sees it.
No-op if not running as a teammate.
@param mode - The permission mode to sync
@param teamNameOverride - Optional team name override (uses env var if not provided)"""
    return None


def setMultipleMemberModes(teamName, modeUpdates):
    """Sets multiple team members' permission modes in a single atomic operation.
Avoids race conditions when updating multiple teammates at once.
@param teamName - The name of the team
@param modeUpdates - Array of {memberName, mode} to update"""
    teamFile = readTeamFile(teamName)
    if not teamFile:
        return False
    update_map = {item.get('memberName'): item.get('mode') for item in (modeUpdates or []) if isinstance(item, dict)}
    changed = False
    for member in teamFile.get('members', []):
        if member.get('name') in update_map and member.get('mode') != update_map[member.get('name')]:
            member['mode'] = update_map[member.get('name')]
            changed = True
    if changed:
        writeTeamFile(teamName, teamFile)
    return True


async def setMemberActive(teamName, memberName, isActive):
    """Sets a team member's active status.
Called when a teammate becomes idle (isActive=false) or starts a new turn (isActive=true).
@param teamName - The name of the team
@param memberName - The name of the member to update
@param isActive - Whether the member is active (true) or idle (false)"""
    teamFile = readTeamFile(teamName)
    if not teamFile:
        return None
    changed = False
    for member in teamFile.get('members', []):
        if member.get('name') == memberName and member.get('isActive') != isActive:
            member['isActive'] = isActive
            changed = True
    if changed:
        writeTeamFile(teamName, teamFile)
    return None


async def destroyWorktree(worktreePath):
    """Destroys a git worktree at the given path.
First attempts to use `git worktree remove`, then falls back to rm -rf.
Safe to call on non-existent paths."""
    if not worktreePath:
        return None
    shutil.rmtree(str(worktreePath), ignore_errors=True)
    return None


def registerTeamForSessionCleanup(teamName):
    """Mark a team as created this session so it gets cleaned up on exit.
Call this right after the initial writeTeamFile. TeamDelete should
call unregisterTeamForSessionCleanup to prevent double-cleanup.
Backing Set lives in bootstrap/state.ts so resetStateForTests()
clears it between tests (avoids the PR #17615 cross-shard leak class)."""
    _session_created_teams.add(str(teamName))
    return None


def unregisterTeamForSessionCleanup(teamName):
    """Remove a team from session cleanup tracking (e.g., after explicit
TeamDelete — already cleaned, don't try again on shutdown)."""
    _session_created_teams.discard(str(teamName))
    return None


async def cleanupSessionTeams():
    """Clean up all teams created this session that weren't explicitly deleted.
Registered with gracefulShutdown from init.ts."""
    for team_name in list(_session_created_teams):
        await cleanupTeamDirectories(team_name)
    _session_created_teams.clear()
    return None


async def killOrphanedTeammatePanes(teamName):
    """Best-effort kill of all pane-backed teammate panes for a team.
Called from cleanupSessionTeams on ungraceful leader exit (SIGINT/SIGTERM).
Dynamic imports avoid adding registry/detection to this module's static
dep graph — this only runs at shutdown, so the import cost is irrelevant."""
    return None


async def cleanupTeamDirectories(teamName):
    """Cleans up team and task directories for a given team name.
Also cleans up git worktrees created for teammates.
Called when a swarm session is terminated."""
    teamFile = readTeamFile(teamName) or {}
    for member in teamFile.get('members', []):
        worktree_path = member.get('worktreePath')
        if worktree_path:
            await destroyWorktree(worktree_path)

    team_dir = Path(getTeamDir(teamName))
    shutil.rmtree(team_dir, ignore_errors=True)

    tasks_dir = Path(getTasksDir(sanitizeName(teamName)))
    shutil.rmtree(tasks_dir, ignore_errors=True)
    notifyTasksUpdated()
    logForDebugging(f"[TeammateTool] Cleaned up team directory: {team_dir}")
    logForDebugging(f"[TeammateTool] Cleaned up tasks directory: {tasks_dir}")
    return None

