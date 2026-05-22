"""
Port of src/utils/teleport/api.ts

Teleport API client — HTTP calls to the Sessions API with OAuth auth,
retry logic and response parsing.
"""
from __future__ import annotations

import asyncio
import uuid as uuid_lib
from typing import Any, Dict, List, Optional, Union

import requests

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CCR_BYOC_BETA = "ccr-byoc-2025-07-29"

TELEPORT_RETRY_DELAYS = [2.0, 4.0, 8.0, 16.0]  # seconds
MAX_TELEPORT_RETRIES = len(TELEPORT_RETRY_DELAYS)

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

SessionStatus = str
GitSource = Dict[str, Any]
KnowledgeBaseSource = Dict[str, Any]
SessionContextSource = Union[GitSource, KnowledgeBaseSource]
OutcomeGitInfo = Dict[str, Any]
GitRepositoryOutcome = Dict[str, Any]
Outcome = GitRepositoryOutcome
SessionContext = Dict[str, Any]
SessionResource = Dict[str, Any]
ListSessionsResponse = Dict[str, Any]
CodeSession = Dict[str, Any]
RemoteMessageContent = Union[str, List[Dict[str, Any]]]


# ---------------------------------------------------------------------------
# Network helpers
# ---------------------------------------------------------------------------

def isTransientNetworkError(error: Exception) -> bool:
    """Return True if *error* is a transient network error that should be retried."""
    if isinstance(error, (requests.exceptions.ConnectionError, requests.exceptions.Timeout)):
        return True
    if isinstance(error, requests.exceptions.HTTPError):
        resp = getattr(error, "response", None)
        if resp is not None and resp.status_code >= 500:
            return True
    return False


async def axiosGetWithRetry(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 15.0,
) -> requests.Response:
    """GET *url* with automatic retry on transient errors (2s→4s→8s→16s backoff)."""
    last_error: Optional[Exception] = None

    for attempt in range(MAX_TELEPORT_RETRIES + 1):
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            resp.raise_for_status()
            return resp
        except Exception as exc:
            last_error = exc
            if not isTransientNetworkError(exc):
                raise
            if attempt >= MAX_TELEPORT_RETRIES:
                raise
            delay = TELEPORT_RETRY_DELAYS[attempt]
            await asyncio.sleep(delay)

    raise last_error  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def _get_oauth_tokens() -> Optional[Dict[str, Any]]:
    try:
        from vivian_cli.utils.auth import getvivianAIOAuthTokens  # type: ignore
        return getvivianAIOAuthTokens()
    except ImportError:
        return None


def _get_base_api_url() -> str:
    try:
        from vivian_cli.utils.configConstants import OAUTH_CONFIG  # type: ignore
        return OAUTH_CONFIG.get("BASE_API_URL", "https://api-vivian.d0a.net")
    except ImportError:
        return "https://api-vivian.d0a.net"


async def _get_organization_uuid() -> Optional[str]:
    try:
        from vivian_cli.utils.auth import getOrganizationUUID  # type: ignore
        result = getOrganizationUUID()
        if asyncio.iscoroutine(result):
            return await result
        return result
    except ImportError:
        return None


def getOAuthHeaders(accessToken: str) -> Dict[str, str]:
    """Build standard OAuth request headers."""
    return {
        "Authorization": f"Bearer {accessToken}",
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01",
    }


# ---------------------------------------------------------------------------
# API preparation
# ---------------------------------------------------------------------------

async def prepareApiRequest() -> Dict[str, str]:
    """Validate auth and return ``{"accessToken": ..., "orgUUID": ...}``."""
    tokens = _get_oauth_tokens()
    access_token = (tokens or {}).get("accessToken")
    if not access_token:
        raise RuntimeError(
            "vivian Code web sessions require authentication with a api-vivian.d0a.net account. "
            "API key authentication is not sufficient. "
            "Please run /login to authenticate, or check your authentication status with /status."
        )

    org_uuid = await _get_organization_uuid()
    if not org_uuid:
        raise RuntimeError("Unable to get organization UUID")

    return {"accessToken": access_token, "orgUUID": org_uuid}


# ---------------------------------------------------------------------------
# Session operations
# ---------------------------------------------------------------------------

def _parse_github_repository(url: str) -> Optional[str]:
    import re
    m = re.search(r"github\.com[:/]([^/]+/[^/.]+?)(?:\.git)?$", url)
    return m.group(1) if m else None


async def fetchCodeSessionsFromSessionsAPI() -> List[CodeSession]:
    """Fetch code sessions from the Sessions API (``/v1/sessions``)."""
    creds = await prepareApiRequest()
    url = f"{_get_base_api_url()}/v1/sessions"

    headers = {
        **getOAuthHeaders(creds["accessToken"]),
        "anthropic-beta": CCR_BYOC_BETA,
        "x-organization-uuid": creds["orgUUID"],
    }

    resp = await axiosGetWithRetry(url, headers=headers)
    data: ListSessionsResponse = resp.json()

    sessions: List[CodeSession] = []
    for session in data.get("data", []):
        sources = session.get("session_context", {}).get("sources", [])
        git_source = next((s for s in sources if s.get("type") == "git_repository"), None)

        repo = None
        if git_source and git_source.get("url"):
            repo_path = _parse_github_repository(git_source["url"])
            if repo_path and "/" in repo_path:
                owner, name = repo_path.split("/", 1)
                repo = {
                    "name": name,
                    "owner": {"login": owner},
                    "default_branch": git_source.get("revision"),
                }

        sessions.append({
            "id": session["id"],
            "title": session.get("title") or "Untitled",
            "description": "",
            "status": session.get("session_status", "idle"),
            "repo": repo,
            "turns": [],
            "created_at": session.get("created_at", ""),
            "updated_at": session.get("updated_at", ""),
        })

    return sessions


async def fetchSession(sessionId: str) -> SessionResource:
    """Fetch a single session by ID from the Sessions API."""
    creds = await prepareApiRequest()
    url = f"{_get_base_api_url()}/v1/sessions/{sessionId}"
    headers = {
        **getOAuthHeaders(creds["accessToken"]),
        "anthropic-beta": CCR_BYOC_BETA,
        "x-organization-uuid": creds["orgUUID"],
    }

    resp = requests.get(url, headers=headers, timeout=15.0)

    if resp.status_code == 404:
        raise RuntimeError(f"Session not found: {sessionId}")
    if resp.status_code == 401:
        raise RuntimeError("Session expired. Please run /login to sign in again.")
    if resp.status_code != 200:
        try:
            error_data = resp.json()
            api_msg = error_data.get("error", {}).get("message", "")
        except Exception:
            api_msg = ""
        raise RuntimeError(api_msg or f"Failed to fetch session: {resp.status_code} {resp.reason}")

    return resp.json()


def getBranchFromSession(session: SessionResource) -> Optional[str]:
    """Return the first branch name from *session*'s git repository outcomes."""
    outcomes = (session.get("session_context") or {}).get("outcomes") or []
    for outcome in outcomes:
        if outcome.get("type") == "git_repository":
            branches = (outcome.get("git_info") or {}).get("branches", [])
            if branches:
                return branches[0]
    return None


async def sendEventToRemoteSession(
    sessionId: str,
    messageContent: RemoteMessageContent,
    opts: Optional[Dict[str, Any]] = None,
) -> bool:
    """Send a user message event to an existing remote session."""
    try:
        creds = await prepareApiRequest()
        url = f"{_get_base_api_url()}/v1/sessions/{sessionId}/events"
        headers = {
            **getOAuthHeaders(creds["accessToken"]),
            "anthropic-beta": CCR_BYOC_BETA,
            "x-organization-uuid": creds["orgUUID"],
        }
        payload = {
            "uuid": (opts or {}).get("uuid") or str(uuid_lib.uuid4()),
            "session_id": sessionId,
            "type": "user",
            "parent_tool_use_id": None,
            "message": {"role": "user", "content": messageContent},
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=15.0)
        return resp.status_code in (200, 201, 202)
    except Exception:
        return False


async def updateSessionTitle(sessionId: str, title: str) -> bool:
    """Update the title of an existing remote session."""
    try:
        creds = await prepareApiRequest()
        url = f"{_get_base_api_url()}/v1/sessions/{sessionId}"
        headers = {
            **getOAuthHeaders(creds["accessToken"]),
            "anthropic-beta": CCR_BYOC_BETA,
            "x-organization-uuid": creds["orgUUID"],
        }
        resp = requests.patch(url, headers=headers, json={"title": title}, timeout=15.0)
        return resp.status_code in (200, 201, 204)
    except Exception:
        return False
