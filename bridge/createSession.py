"""Port of src/bridge/createSession.ts

Session creation/fetch/archive/update helpers for bridge sessions.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

import httpx

from .debugUtils import extractErrorDetail
from .sessionIdCompat import toCompatSessionId


def _debug(msg: str) -> None:
    try:
        from ..utils.debug import log_for_debugging
        log_for_debugging(msg)
    except Exception:
        pass


def _get_ccr_headers(access_token: str, org_uuid: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01",
        "anthropic-beta": "ccr-byoc-2025-07-29",
        "x-organization-uuid": org_uuid,
    }


async def _get_access_token_and_org(
    get_access_token: Optional[Callable[[], Optional[str]]] = None,
) -> Optional[tuple]:
    """Returns (access_token, org_uuid) or None."""
    try:
        from ..utils.auth import get_vivian_ai_oauth_tokens
        from ..services.oauth.client import get_organization_uuid
    except Exception:
        return None

    access_token = None
    if get_access_token:
        access_token = get_access_token()
    if not access_token:
        tokens = get_vivian_ai_oauth_tokens()
        if tokens:
            access_token = tokens.get("accessToken")
    if not access_token:
        return None

    org_uuid = await get_organization_uuid()
    if not org_uuid:
        return None

    return access_token, org_uuid


def _get_base_api_url(base_url: Optional[str] = None) -> str:
    if base_url:
        return base_url
    try:
        from ..constants.oauth import get_oauth_config
        return get_oauth_config().get("BASE_API_URL", "https://api-vivian.d0a.net")
    except Exception:
        return "https://api-vivian.d0a.net"


async def createBridgeSession(
    environment_id: str,
    events: List[Dict[str, Any]],
    git_repo_url: Optional[str],
    branch: str,
    signal: Any = None,
    title: Optional[str] = None,
    base_url: Optional[str] = None,
    get_access_token: Optional[Callable[[], Optional[str]]] = None,
    permission_mode: Optional[str] = None,
) -> Optional[str]:
    """Create a session on a bridge environment via POST /v1/sessions."""
    result = await _get_access_token_and_org(get_access_token)
    if not result:
        _debug("[bridge] No access token or org UUID for session creation")
        return None
    access_token, org_uuid = result

    git_source = None
    git_outcome = None
    if git_repo_url:
        try:
            from ..utils.detect_repository import parse_git_remote, parse_github_repository
            parsed = parse_git_remote(git_repo_url)
            if parsed:
                host, owner, name = parsed.get("host"), parsed.get("owner"), parsed.get("name")
                try:
                    from ..utils.git import get_default_branch
                    revision = branch or await get_default_branch() or None
                except Exception:
                    revision = branch or None
                if host and owner and name:
                    git_source = {"type": "git_repository", "url": f"https://{host}/{owner}/{name}", "revision": revision}
                    git_outcome = {"type": "git_repository", "git_info": {"type": "github", "repo": f"{owner}/{name}", "branches": [f"vivian/{branch or 'task'}"]}}
            else:
                owner_repo = parse_github_repository(git_repo_url)
                if owner_repo and "/" in owner_repo:
                    owner, name = owner_repo.split("/", 1)
                    try:
                        from ..utils.git import get_default_branch
                        revision = branch or await get_default_branch() or None
                    except Exception:
                        revision = branch or None
                    git_source = {"type": "git_repository", "url": f"https://github.com/{owner}/{name}", "revision": revision}
                    git_outcome = {"type": "git_repository", "git_info": {"type": "github", "repo": f"{owner}/{name}", "branches": [f"vivian/{branch or 'task'}"]}}
        except Exception:
            pass

    try:
        from ..utils.model.model import get_main_loop_model
        model = get_main_loop_model()
    except Exception:
        model = "vivian-opus-4-5"

    request_body: Dict[str, Any] = {
        "events": events,
        "session_context": {
            "sources": [git_source] if git_source else [],
            "outcomes": [git_outcome] if git_outcome else [],
            "model": model,
        },
        "environment_id": environment_id,
        "source": "remote-control",
    }
    if title is not None:
        request_body["title"] = title
    if permission_mode:
        request_body["permission_mode"] = permission_mode

    headers = _get_ccr_headers(access_token, org_uuid)
    url = f"{_get_base_api_url(base_url)}/v1/sessions"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=request_body, headers=headers)
    except Exception as err:
        _debug(f"[bridge] Session creation request failed: {err}")
        return None

    if resp.status_code not in (200, 201):
        try:
            detail = extractErrorDetail(resp.json())
        except Exception:
            detail = None
        _debug(f"[bridge] Session creation failed with status {resp.status_code}" + (f": {detail}" if detail else ""))
        return None

    try:
        session_data = resp.json()
        session_id = session_data["id"]
        return session_id
    except Exception:
        _debug("[bridge] No session ID in response")
        return None


async def getBridgeSession(
    session_id: str,
    base_url: Optional[str] = None,
    get_access_token: Optional[Callable[[], Optional[str]]] = None,
) -> Optional[Dict[str, Any]]:
    """Fetch a bridge session via GET /v1/sessions/{id}."""
    result = await _get_access_token_and_org(get_access_token)
    if not result:
        _debug("[bridge] No access token or org UUID for session fetch")
        return None
    access_token, org_uuid = result

    headers = _get_ccr_headers(access_token, org_uuid)
    url = f"{_get_base_api_url(base_url)}/v1/sessions/{session_id}"
    _debug(f"[bridge] Fetching session {session_id}")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers)
    except Exception as err:
        _debug(f"[bridge] Session fetch request failed: {err}")
        return None

    if resp.status_code != 200:
        try:
            detail = extractErrorDetail(resp.json())
        except Exception:
            detail = None
        _debug(f"[bridge] Session fetch failed with status {resp.status_code}" + (f": {detail}" if detail else ""))
        return None

    try:
        return resp.json()
    except Exception:
        return {}


async def archiveBridgeSession(
    session_id: str,
    base_url: Optional[str] = None,
    get_access_token: Optional[Callable[[], Optional[str]]] = None,
    timeout_ms: int = 10_000,
) -> None:
    """Archive a bridge session via POST /v1/sessions/{id}/archive."""
    result = await _get_access_token_and_org(get_access_token)
    if not result:
        _debug("[bridge] No access token or org UUID for session archive")
        return
    access_token, org_uuid = result

    headers = _get_ccr_headers(access_token, org_uuid)
    url = f"{_get_base_api_url(base_url)}/v1/sessions/{session_id}/archive"
    _debug(f"[bridge] Archiving session {session_id}")

    resp = await httpx.AsyncClient(timeout=timeout_ms / 1000.0).__aenter__()
    try:
        async with httpx.AsyncClient(timeout=timeout_ms / 1000.0) as client:
            resp = await client.post(url, json={}, headers=headers)
        if resp.status_code == 200:
            _debug(f"[bridge] Session {session_id} archived successfully")
        else:
            try:
                detail = extractErrorDetail(resp.json())
            except Exception:
                detail = None
            _debug(f"[bridge] Session archive failed with status {resp.status_code}" + (f": {detail}" if detail else ""))
    except Exception:
        pass


async def updateBridgeSessionTitle(
    session_id: str,
    title: str,
    base_url: Optional[str] = None,
    get_access_token: Optional[Callable[[], Optional[str]]] = None,
) -> None:
    """Update the title of a bridge session via PATCH /v1/sessions/{id}."""
    result = await _get_access_token_and_org(get_access_token)
    if not result:
        _debug("[bridge] No access token or org UUID for session title update")
        return
    access_token, org_uuid = result

    headers = _get_ccr_headers(access_token, org_uuid)
    compat_id = toCompatSessionId(session_id)
    url = f"{_get_base_api_url(base_url)}/v1/sessions/{compat_id}"
    _debug(f"[bridge] Updating session title: {compat_id} → {title}")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.patch(url, json={"title": title}, headers=headers)
        if resp.status_code == 200:
            _debug("[bridge] Session title updated successfully")
        else:
            try:
                detail = extractErrorDetail(resp.json())
            except Exception:
                detail = None
            _debug(f"[bridge] Session title update failed with status {resp.status_code}" + (f": {detail}" if detail else ""))
    except Exception as err:
        _debug(f"[bridge] Session title update request failed: {err}")
