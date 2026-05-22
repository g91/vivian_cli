"""Port of src/bridge/types.ts

Protocol types for the bridge environments API and dependency interfaces.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, TypedDict

# --- Constants ---

DEFAULT_SESSION_TIMEOUT_MS = 24 * 60 * 60 * 1000

BRIDGE_LOGIN_INSTRUCTION = (
    "Remote Control is only available with api-vivian.d0a.net subscriptions. "
    "Please use `/login` to sign in with your api-vivian.d0a.net account."
)

BRIDGE_LOGIN_ERROR = (
    "Error: You must be logged in to use Remote Control.\n\n"
    + BRIDGE_LOGIN_INSTRUCTION
)

REMOTE_CONTROL_DISCONNECTED_MSG = "Remote Control disconnected."

# --- Protocol types ---

SessionDoneStatus = Literal["completed", "failed", "interrupted"]
SessionActivityType = Literal["tool_start", "text", "result", "error"]
SpawnMode = Literal["single-session", "worktree", "same-dir"]
BridgeWorkerType = Literal["vivian_code", "vivian_code_assistant"]


class WorkData(TypedDict):
    type: Literal["session", "healthcheck"]
    id: str


class WorkResponse(TypedDict):
    id: str
    type: Literal["work"]
    environment_id: str
    state: str
    data: WorkData
    secret: str
    created_at: str


class WorkSecret(TypedDict, total=False):
    version: int
    session_ingress_token: str
    api_base_url: str
    sources: List[Dict[str, Any]]
    auth: List[Dict[str, str]]
    vivian_code_args: Optional[Dict[str, str]]
    mcp_config: Any
    environment_variables: Optional[Dict[str, str]]
    use_code_sessions: bool


class SessionActivity(TypedDict):
    type: SessionActivityType
    summary: str
    timestamp: int


class BridgeConfig(TypedDict, total=False):
    dir: str
    machineName: str
    branch: str
    gitRepoUrl: Optional[str]
    maxSessions: int
    spawnMode: SpawnMode
    verbose: bool
    sandbox: bool
    bridgeId: str
    workerType: str
    environmentId: str
    reuseEnvironmentId: Optional[str]
    apiBaseUrl: str
    sessionIngressUrl: str
    debugFile: Optional[str]
    sessionTimeoutMs: Optional[int]


class PermissionResponseEvent(TypedDict):
    type: Literal["control_response"]
    response: Dict[str, Any]


class SessionSpawnOpts(TypedDict, total=False):
    sessionId: str
    sdkUrl: str
    accessToken: str
    useCcrV2: bool
    workerEpoch: int
    onFirstUserMessage: Any  # callable


# --- Abstract interfaces (Python protocol classes) ---

class BridgeApiClient:
    """Protocol interface for bridge API client implementations."""

    async def registerBridgeEnvironment(self, config: BridgeConfig) -> Dict[str, str]:
        raise NotImplementedError

    async def pollForWork(
        self,
        environment_id: str,
        environment_secret: str,
        signal: Any = None,
        reclaim_older_than_ms: Optional[int] = None,
    ) -> Optional[WorkResponse]:
        raise NotImplementedError

    async def acknowledgeWork(
        self,
        environment_id: str,
        work_id: str,
        session_token: str,
    ) -> None:
        raise NotImplementedError

    async def stopWork(self, environment_id: str, work_id: str, force: bool) -> None:
        raise NotImplementedError

    async def deregisterEnvironment(self, environment_id: str) -> None:
        raise NotImplementedError

    async def sendPermissionResponseEvent(
        self,
        session_id: str,
        event: PermissionResponseEvent,
        session_token: str,
    ) -> None:
        raise NotImplementedError

    async def archiveSession(self, session_id: str) -> None:
        raise NotImplementedError

    async def reconnectSession(self, environment_id: str, session_id: str) -> None:
        raise NotImplementedError

    async def heartbeatWork(
        self,
        environment_id: str,
        work_id: str,
        session_token: str,
    ) -> Dict[str, Any]:
        raise NotImplementedError


class SessionHandle:
    """Interface for an active session managed by a SessionSpawner."""

    sessionId: str
    activities: List[SessionActivity]
    currentActivity: Optional[SessionActivity]
    accessToken: str
    lastStderr: List[str]

    def kill(self) -> None:
        raise NotImplementedError

    def forceKill(self) -> None:
        raise NotImplementedError

    def writeStdin(self, data: str) -> None:
        raise NotImplementedError

    def updateAccessToken(self, token: str) -> None:
        raise NotImplementedError


class SessionSpawner:
    """Interface for spawning child vivian Code sessions."""

    def spawn(self, opts: SessionSpawnOpts, directory: str) -> SessionHandle:
        raise NotImplementedError


class BridgeLogger:
    """Interface for bridge logging/display."""

    def printBanner(self, config: BridgeConfig, environment_id: str) -> None: ...
    def logSessionStart(self, session_id: str, prompt: str) -> None: ...
    def logSessionComplete(self, session_id: str, duration_ms: int) -> None: ...
    def logSessionFailed(self, session_id: str, error: str) -> None: ...
    def logStatus(self, message: str) -> None: ...
    def logVerbose(self, message: str) -> None: ...
    def logError(self, message: str) -> None: ...
    def logReconnected(self, disconnected_ms: int) -> None: ...
    def updateIdleStatus(self) -> None: ...
    def updateReconnectingStatus(self, delay_str: str, elapsed_str: str) -> None: ...
    def updateSessionStatus(self, session_id: str, elapsed: str, activity: SessionActivity, trail: List[str]) -> None: ...
    def clearStatus(self) -> None: ...
    def setRepoInfo(self, repo_name: str, branch: str) -> None: ...
    def setDebugLogPath(self, path: str) -> None: ...
    def setAttached(self, session_id: str) -> None: ...
    def updateFailedStatus(self, error: str) -> None: ...
    def toggleQr(self) -> None: ...
    def updateSessionCount(self, active: int, max_sessions: int, mode: SpawnMode) -> None: ...
    def setSpawnModeDisplay(self, mode: Optional[str]) -> None: ...
    def addSession(self, session_id: str, url: str) -> None: ...
    def updateSessionActivity(self, session_id: str, activity: SessionActivity) -> None: ...
    def setSessionTitle(self, session_id: str, title: str) -> None: ...
    def removeSession(self, session_id: str) -> None: ...
    def refreshDisplay(self) -> None: ...
