"""Port of src/utils/swarm/permissionSync.ts."""
from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any

from ..debug import logForDebugging
from .teamHelpers import getTeamDir, readTeamFileAsync


SwarmPermissionRequest = dict[str, Any]
PermissionResolution = dict[str, Any]
PermissionResponse = dict[str, Any]
SwarmPermissionRequestSchema: Any = None


def getPermissionDir(teamName: str) -> str:
    return str(Path(getTeamDir(teamName)) / "permissions")


def getPendingDir(teamName: str) -> str:
    return str(Path(getPermissionDir(teamName)) / "pending")


def getResolvedDir(teamName: str) -> str:
    return str(Path(getPermissionDir(teamName)) / "resolved")


async def ensurePermissionDirsAsync(teamName: str) -> None:
    for path in (getPermissionDir(teamName), getPendingDir(teamName), getResolvedDir(teamName)):
        Path(path).mkdir(parents=True, exist_ok=True)


def getPendingRequestPath(teamName: str, requestId: str) -> str:
    return str(Path(getPendingDir(teamName)) / f"{requestId}.json")


def getResolvedRequestPath(teamName: str, requestId: str) -> str:
    return str(Path(getResolvedDir(teamName)) / f"{requestId}.json")


def generateRequestId() -> str:
    return f"perm-{int(time.time() * 1000)}-{uuid.uuid4().hex[:7]}"


def createPermissionRequest(params: dict[str, Any] | None = None) -> SwarmPermissionRequest:
    params = params or {}
    team_name = params.get("teamName") or _team_name()
    worker_id = params.get("workerId") or _agent_id()
    worker_name = params.get("workerName") or _agent_name()
    worker_color = params.get("workerColor") or _agent_color()
    if not team_name:
        raise ValueError("Team name is required for permission requests")
    if not worker_name:
        raise ValueError("Worker name is required for permission requests")
    if not worker_id:
        worker_id = worker_name

    return {
        "id": generateRequestId(),
        "workerId": worker_id,
        "workerName": worker_name,
        "workerColor": worker_color,
        "teamName": team_name,
        "toolName": params["toolName"],
        "toolUseId": params["toolUseId"],
        "description": params["description"],
        "input": params.get("input") or {},
        "permissionSuggestions": params.get("permissionSuggestions") or [],
        "status": "pending",
        "createdAt": int(time.time() * 1000),
    }


async def writePermissionRequest(request: SwarmPermissionRequest) -> SwarmPermissionRequest:
    await ensurePermissionDirsAsync(request["teamName"])
    path = Path(getPendingRequestPath(request["teamName"], request["id"]))
    path.write_text(json.dumps(request, indent=2, sort_keys=True), encoding="utf-8")
    logForDebugging(
        f"[PermissionSync] Wrote pending request {request['id']} from {request['workerName']} for {request['toolName']}"
    )
    return request


async def readPendingPermissions(teamName: str | None = None) -> list[SwarmPermissionRequest]:
    team = teamName or _team_name()
    if not team:
        return []
    pending_dir = Path(getPendingDir(team))
    if not pending_dir.exists():
        return []

    requests: list[SwarmPermissionRequest] = []
    for path in sorted(pending_dir.glob("*.json")):
        try:
            requests.append(json.loads(path.read_text(encoding="utf-8")))
        except Exception as error:
            logForDebugging(f"[PermissionSync] Failed to read request file {path.name}: {error}")
    requests.sort(key=lambda item: item.get("createdAt", 0))
    return requests


async def readResolvedPermission(
    requestId: str,
    teamName: str | None = None,
) -> SwarmPermissionRequest | None:
    team = teamName or _team_name()
    if not team:
        return None
    path = Path(getResolvedRequestPath(team, requestId))
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as error:
        logForDebugging(f"[PermissionSync] Failed to read resolved request {requestId}: {error}")
        return None


async def resolvePermission(
    requestId: str,
    resolution: PermissionResolution,
    teamName: str | None = None,
) -> bool:
    team = teamName or _team_name()
    if not team:
        return False
    await ensurePermissionDirsAsync(team)
    pending_path = Path(getPendingRequestPath(team, requestId))
    if not pending_path.exists():
        return False

    try:
        request = json.loads(pending_path.read_text(encoding="utf-8"))
    except Exception as error:
        logForDebugging(f"[PermissionSync] Failed to parse pending request {requestId}: {error}")
        return False

    resolved_request = {
        **request,
        "status": "approved" if resolution.get("decision") == "approved" else "rejected",
        "resolvedBy": resolution.get("resolvedBy"),
        "resolvedAt": int(time.time() * 1000),
        "feedback": resolution.get("feedback"),
        "updatedInput": resolution.get("updatedInput"),
        "permissionUpdates": resolution.get("permissionUpdates"),
    }

    resolved_path = Path(getResolvedRequestPath(team, requestId))
    resolved_path.write_text(json.dumps(resolved_request, indent=2, sort_keys=True), encoding="utf-8")
    pending_path.unlink(missing_ok=True)
    logForDebugging(f"[PermissionSync] Resolved request {requestId} with {resolution.get('decision')}")
    return True


async def cleanupOldResolutions(maxAgeMs: int = 3600000, teamName: str | None = None) -> int:
    team = teamName or _team_name()
    if not team:
        return 0
    resolved_dir = Path(getResolvedDir(team))
    if not resolved_dir.exists():
        return 0

    now_ms = int(time.time() * 1000)
    cleaned = 0
    for path in resolved_dir.glob("*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            resolved_at = payload.get("resolvedAt") or payload.get("createdAt") or 0
        except Exception:
            resolved_at = 0
        if now_ms - int(resolved_at) >= maxAgeMs:
            path.unlink(missing_ok=True)
            cleaned += 1
    return cleaned


async def pollForResponse(
    requestId: str,
    _agentName: str | None = None,
    teamName: str | None = None,
) -> PermissionResponse | None:
    resolved = await readResolvedPermission(requestId, teamName)
    if not resolved:
        return None
    return {
        "requestId": resolved["id"],
        "decision": "approved" if resolved.get("status") == "approved" else "rejected",
        "timestamp": resolved.get("resolvedAt") or resolved.get("createdAt"),
        "feedback": resolved.get("feedback"),
        "updatedInput": resolved.get("updatedInput"),
        "permissionUpdates": resolved.get("permissionUpdates") or [],
    }


async def removeWorkerResponse(
    requestId: str,
    _agentName: str | None = None,
    teamName: str | None = None,
) -> None:
    await deleteResolvedPermission(requestId, teamName)


def isTeamLeader(teamName: str | None = None) -> bool:
    team = teamName or _team_name()
    if not team:
        return False
    agent_id = _agent_id()
    return not agent_id or agent_id == "team-lead"


def isSwarmWorker() -> bool:
    return bool(_team_name() and _agent_id() and not isTeamLeader())


async def deleteResolvedPermission(requestId: str, teamName: str | None = None) -> bool:
    team = teamName or _team_name()
    if not team:
        return False
    path = Path(getResolvedRequestPath(team, requestId))
    if not path.exists():
        return False
    path.unlink(missing_ok=True)
    return True


async def getLeaderName(teamName: str | None = None) -> str | None:
    team = teamName or _team_name()
    if not team:
        return None
    team_file = await readTeamFileAsync(team)
    if not team_file:
        return "team-lead"
    lead_agent_id = team_file.get("leadAgentId")
    for member in team_file.get("members", []):
        if member.get("agentId") == lead_agent_id:
            return member.get("name") or "team-lead"
    return "team-lead"


async def sendPermissionRequestViaMailbox(request: SwarmPermissionRequest) -> bool:
    await writePermissionRequest(request)
    return True


async def sendPermissionResponseViaMailbox(
    workerName: str,
    resolution: PermissionResolution,
    requestId: str,
    teamName: str | None = None,
) -> bool:
    _ = workerName
    return await resolvePermission(requestId, resolution, teamName)


def generateSandboxRequestId() -> str:
    return f"sandbox-{int(time.time() * 1000)}-{uuid.uuid4().hex[:7]}"


async def sendSandboxPermissionRequestViaMailbox(host: str, requestId: str, teamName: str | None = None) -> bool:
    _ = host, requestId, teamName
    return False


async def sendSandboxPermissionResponseViaMailbox(
    workerName: str,
    requestId: str,
    host: str,
    allow: bool,
    teamName: str | None = None,
) -> bool:
    _ = workerName, requestId, host, allow, teamName
    return False


submitPermissionRequest = writePermissionRequest


def _team_name() -> str | None:
    return os.environ.get("vivian_CODE_TEAM_NAME")


def _agent_id() -> str | None:
    return os.environ.get("vivian_CODE_AGENT_ID")


def _agent_name() -> str | None:
    return os.environ.get("vivian_CODE_AGENT_NAME")


def _agent_color() -> str | None:
    return os.environ.get("vivian_CODE_AGENT_COLOR")
