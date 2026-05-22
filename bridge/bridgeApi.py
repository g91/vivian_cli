"""Port of src/bridge/bridgeApi.ts

Bridge API client — HTTP wrappers for the environments API.
"""
from __future__ import annotations

import asyncio
import inspect
import re
from typing import Any, Callable, Dict, Optional

import httpx

from .debugUtils import debugBody, extractErrorDetail
from .types import (
    BRIDGE_LOGIN_INSTRUCTION,
    BridgeApiClient,
    BridgeConfig,
    PermissionResponseEvent,
    WorkResponse,
)

BETA_HEADER = "environments-2025-11-01"
SAFE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


def validateBridgeId(id_: str, label: str) -> str:
    """Validate a server-provided ID is safe for URL interpolation."""
    if not id_ or not SAFE_ID_PATTERN.match(id_):
        raise ValueError(f"Invalid {label}: contains unsafe characters")
    return id_


class BridgeFatalError(Exception):
    """Fatal bridge errors that should not be retried."""

    def __init__(self, message: str, status: int, error_type: Optional[str] = None) -> None:
        super().__init__(message)
        self.status = status
        self.errorType = error_type


def isExpiredErrorType(error_type: Optional[str]) -> bool:
    if not error_type:
        return False
    return "expired" in error_type or "lifetime" in error_type


def isSuppressible403(err: BridgeFatalError) -> bool:
    if err.status != 403:
        return False
    return "external_poll_sessions" in str(err) or "environments:manage" in str(err)


def _extract_error_type(data: Any) -> Optional[str]:
    if isinstance(data, dict):
        error_obj = data.get("error")
        if isinstance(error_obj, dict) and isinstance(error_obj.get("type"), str):
            return error_obj["type"]
    return None


def _handle_error_status(status: int, data: Any, context: str) -> None:
    if status in (200, 204):
        return
    detail = extractErrorDetail(data)
    error_type = _extract_error_type(data)

    if status == 401:
        raise BridgeFatalError(
            f"{context}: Authentication failed (401)" + (f": {detail}" if detail else "") + f". {BRIDGE_LOGIN_INSTRUCTION}",
            401, error_type,
        )
    if status == 403:
        if isExpiredErrorType(error_type):
            raise BridgeFatalError(
                "Remote Control session has expired. Please restart with `vivian remote-control` or /remote-control.",
                403, error_type,
            )
        raise BridgeFatalError(
            f"{context}: Access denied (403)" + (f": {detail}" if detail else "") + ". Check your organization permissions.",
            403, error_type,
        )
    if status == 404:
        raise BridgeFatalError(
            detail or f"{context}: Not found (404). Remote Control may not be available for this organization.",
            404, error_type,
        )
    if status == 410:
        raise BridgeFatalError(
            detail or "Remote Control session has expired. Please restart with `vivian remote-control` or /remote-control.",
            410, error_type or "environment_expired",
        )
    if status == 429:
        raise RuntimeError(f"{context}: Rate limited (429). Polling too frequently.")
    raise RuntimeError(f"{context}: Failed with status {status}" + (f": {detail}" if detail else ""))


async def _invoke_auth_refresh(callback: Callable[..., Any], stale_token: str) -> Any:
    try:
        params = inspect.signature(callback).parameters
        maybe = callback(stale_token) if len(params) >= 1 else callback()
    except (TypeError, ValueError):
        maybe = callback(stale_token)
    if asyncio.iscoroutine(maybe):
        return await maybe
    return maybe


def createBridgeApiClient(
    base_url: str,
    get_access_token: Callable[[], Optional[str]],
    runner_version: str,
    on_debug: Optional[Callable[[str], None]] = None,
    on_auth_401: Optional[Callable[[str], Any]] = None,  # async callable
    get_trusted_device_token: Optional[Callable[[], Optional[str]]] = None,
) -> "HttpBridgeApiClient":
    return HttpBridgeApiClient(
        base_url=base_url,
        get_access_token=get_access_token,
        runner_version=runner_version,
        on_debug=on_debug,
        on_auth_401=on_auth_401,
        get_trusted_device_token=get_trusted_device_token,
    )


class HttpBridgeApiClient(BridgeApiClient):
    """HTTP implementation of BridgeApiClient."""

    def __init__(
        self,
        base_url: str,
        get_access_token: Callable[[], Optional[str]],
        runner_version: str,
        on_debug: Optional[Callable[[str], None]] = None,
        on_auth_401: Optional[Callable] = None,
        get_trusted_device_token: Optional[Callable[[], Optional[str]]] = None,
    ) -> None:
        self._base_url = base_url
        self._get_access_token = get_access_token
        self._runner_version = runner_version
        self._on_debug = on_debug
        self._on_auth_401 = on_auth_401
        self._get_trusted_device_token = get_trusted_device_token
        self._consecutive_empty_polls = 0
        self._EMPTY_POLL_LOG_INTERVAL = 100

    def _debug(self, msg: str) -> None:
        if self._on_debug:
            self._on_debug(msg)

    def _get_headers(self, access_token: str) -> Dict[str, str]:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
            "anthropic-beta": BETA_HEADER,
            "x-environment-runner-version": self._runner_version,
        }
        if self._get_trusted_device_token:
            token = self._get_trusted_device_token()
            if token:
                headers["X-Trusted-Device-Token"] = token
        return headers

    def _resolve_auth(self) -> str:
        token = self._get_access_token()
        if not token:
            raise RuntimeError(BRIDGE_LOGIN_INSTRUCTION)
        return token

    async def _with_oauth_retry(self, fn: Callable, context: str) -> Any:
        """Execute request with a single retry on 401 after token refresh."""
        access_token = self._resolve_auth()
        resp = await fn(access_token)
        if resp.status_code != 401:
            return resp
        if not self._on_auth_401:
            self._debug(f"[bridge:api] {context}: 401 received, no refresh handler")
            return resp
        self._debug(f"[bridge:api] {context}: 401 received, attempting token refresh")
        refreshed = await _invoke_auth_refresh(self._on_auth_401, access_token)
        if refreshed:
            self._debug(f"[bridge:api] {context}: Token refreshed, retrying request")
            new_token = self._resolve_auth()
            retry_resp = await fn(new_token)
            if retry_resp.status_code != 401:
                return retry_resp
            self._debug(f"[bridge:api] {context}: Retry after refresh also got 401")
        else:
            self._debug(f"[bridge:api] {context}: Token refresh failed")
        return resp

    async def registerBridgeEnvironment(self, config: BridgeConfig) -> Dict[str, str]:
        self._debug(f"[bridge:api] POST /v1/environments/bridge bridgeId={config.get('bridgeId')}")
        payload: Dict[str, Any] = {
            "machine_name": config.get("machineName"),
            "directory": config.get("dir"),
            "branch": config.get("branch"),
            "git_repo_url": config.get("gitRepoUrl"),
            "max_sessions": config.get("maxSessions"),
            "metadata": {"worker_type": config.get("workerType")},
        }
        if config.get("reuseEnvironmentId"):
            payload["environment_id"] = config["reuseEnvironmentId"]

        async def _request(token: str):
            async with httpx.AsyncClient(timeout=15.0) as client:
                return await client.post(
                    f"{self._base_url}/v1/environments/bridge",
                    json=payload,
                    headers=self._get_headers(token),
                )

        resp = await self._with_oauth_retry(_request, "Registration")
        data = resp.json() if resp.content else {}
        _handle_error_status(resp.status_code, data, "Registration")
        self._debug(f"[bridge:api] POST /v1/environments/bridge -> {resp.status_code} environment_id={data.get('environment_id')}")
        return data

    async def pollForWork(
        self,
        environment_id: str,
        environment_secret: str,
        signal: Any = None,
        reclaim_older_than_ms: Optional[int] = None,
    ) -> Optional[WorkResponse]:
        validateBridgeId(environment_id, "environmentId")
        prev_empty = self._consecutive_empty_polls
        self._consecutive_empty_polls = 0

        params: Dict[str, Any] = {}
        if reclaim_older_than_ms is not None:
            params["reclaim_older_than_ms"] = reclaim_older_than_ms

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self._base_url}/v1/environments/{environment_id}/work/poll",
                    headers=self._get_headers(environment_secret),
                    params=params,
                )
        except Exception as e:
            raise

        data = resp.json() if resp.content else None
        _handle_error_status(resp.status_code, data, "Poll")

        if not data:
            self._consecutive_empty_polls = prev_empty + 1
            if (self._consecutive_empty_polls == 1 or
                    self._consecutive_empty_polls % self._EMPTY_POLL_LOG_INTERVAL == 0):
                self._debug(f"[bridge:api] GET .../work/poll -> {resp.status_code} (no work, {self._consecutive_empty_polls} consecutive empty polls)")
            return None

        self._debug(f"[bridge:api] GET .../work/poll -> {resp.status_code} workId={data.get('id')} type={data.get('data', {}).get('type')}")
        return data

    async def acknowledgeWork(self, environment_id: str, work_id: str, session_token: str) -> None:
        validateBridgeId(environment_id, "environmentId")
        validateBridgeId(work_id, "workId")
        self._debug(f"[bridge:api] POST .../work/{work_id}/ack")
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{self._base_url}/v1/environments/{environment_id}/work/{work_id}/ack",
                json={},
                headers=self._get_headers(session_token),
            )
        data = resp.json() if resp.content else {}
        _handle_error_status(resp.status_code, data, "Acknowledge")
        self._debug(f"[bridge:api] POST .../work/{work_id}/ack -> {resp.status_code}")

    async def stopWork(self, environment_id: str, work_id: str, force: bool) -> None:
        validateBridgeId(environment_id, "environmentId")
        validateBridgeId(work_id, "workId")
        self._debug(f"[bridge:api] POST .../work/{work_id}/stop force={force}")

        async def _request(token: str):
            async with httpx.AsyncClient(timeout=10.0) as client:
                return await client.post(
                    f"{self._base_url}/v1/environments/{environment_id}/work/{work_id}/stop",
                    json={"force": force},
                    headers=self._get_headers(token),
                )

        resp = await self._with_oauth_retry(_request, "StopWork")
        data = resp.json() if resp.content else {}
        _handle_error_status(resp.status_code, data, "StopWork")
        self._debug(f"[bridge:api] POST .../work/{work_id}/stop -> {resp.status_code}")

    async def deregisterEnvironment(self, environment_id: str) -> None:
        validateBridgeId(environment_id, "environmentId")
        self._debug(f"[bridge:api] DELETE /v1/environments/bridge/{environment_id}")

        async def _request(token: str):
            async with httpx.AsyncClient(timeout=10.0) as client:
                return await client.delete(
                    f"{self._base_url}/v1/environments/bridge/{environment_id}",
                    headers=self._get_headers(token),
                )

        resp = await self._with_oauth_retry(_request, "Deregister")
        data = resp.json() if resp.content else {}
        _handle_error_status(resp.status_code, data, "Deregister")
        self._debug(f"[bridge:api] DELETE /v1/environments/bridge/{environment_id} -> {resp.status_code}")

    async def archiveSession(self, session_id: str) -> None:
        validateBridgeId(session_id, "sessionId")
        self._debug(f"[bridge:api] POST /v1/sessions/{session_id}/archive")

        async def _request(token: str):
            async with httpx.AsyncClient(timeout=10.0) as client:
                return await client.post(
                    f"{self._base_url}/v1/sessions/{session_id}/archive",
                    json={},
                    headers=self._get_headers(token),
                )

        resp = await self._with_oauth_retry(_request, "ArchiveSession")
        if resp.status_code == 409:
            self._debug(f"[bridge:api] POST /v1/sessions/{session_id}/archive -> 409 (already archived)")
            return
        data = resp.json() if resp.content else {}
        _handle_error_status(resp.status_code, data, "ArchiveSession")
        self._debug(f"[bridge:api] POST /v1/sessions/{session_id}/archive -> {resp.status_code}")

    async def reconnectSession(self, environment_id: str, session_id: str) -> None:
        validateBridgeId(environment_id, "environmentId")
        validateBridgeId(session_id, "sessionId")
        self._debug(f"[bridge:api] POST /v1/environments/{environment_id}/bridge/reconnect session_id={session_id}")

        async def _request(token: str):
            async with httpx.AsyncClient(timeout=10.0) as client:
                return await client.post(
                    f"{self._base_url}/v1/environments/{environment_id}/bridge/reconnect",
                    json={"session_id": session_id},
                    headers=self._get_headers(token),
                )

        resp = await self._with_oauth_retry(_request, "ReconnectSession")
        data = resp.json() if resp.content else {}
        _handle_error_status(resp.status_code, data, "ReconnectSession")
        self._debug(f"[bridge:api] POST .../bridge/reconnect -> {resp.status_code}")

    async def heartbeatWork(
        self,
        environment_id: str,
        work_id: str,
        session_token: str,
    ) -> Dict[str, Any]:
        validateBridgeId(environment_id, "environmentId")
        validateBridgeId(work_id, "workId")
        self._debug(f"[bridge:api] POST .../work/{work_id}/heartbeat")
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{self._base_url}/v1/environments/{environment_id}/work/{work_id}/heartbeat",
                json={},
                headers=self._get_headers(session_token),
            )
        data = resp.json() if resp.content else {}
        _handle_error_status(resp.status_code, data, "Heartbeat")
        self._debug(f"[bridge:api] POST .../work/{work_id}/heartbeat -> {resp.status_code} lease_extended={data.get('lease_extended')} state={data.get('state')}")
        return data

    async def sendPermissionResponseEvent(
        self,
        session_id: str,
        event: PermissionResponseEvent,
        session_token: str,
    ) -> None:
        validateBridgeId(session_id, "sessionId")
        self._debug(f"[bridge:api] POST /v1/sessions/{session_id}/events type={event.get('type')}")
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{self._base_url}/v1/sessions/{session_id}/events",
                json={"events": [event]},
                headers=self._get_headers(session_token),
            )
        data = resp.json() if resp.content else {}
        _handle_error_status(resp.status_code, data, "SendPermissionResponseEvent")
        self._debug(f"[bridge:api] POST /v1/sessions/{session_id}/events -> {resp.status_code}")
