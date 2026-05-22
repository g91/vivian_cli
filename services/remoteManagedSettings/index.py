"""Remote managed settings — mirrors src/services/remoteManagedSettings/index.ts."""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional

import httpx

from .syncCache import isRemoteManagedSettingsEligible, resetSyncCache
from .syncCacheState import getRemoteManagedSettingsSyncFromCache, getSettingsPath, setSessionCache
from .securityCheck import checkManagedSettingsSecurity, handleSecurityCheckResult
from .types import RemoteManagedSettingsFetchResult
from ...constants.oauth import get_oauth_config
from ...utils.auth import check_and_refresh_oauth_token_if_needed, get_anthropic_api_key, get_vivian_ai_oauth_tokens
from ...utils.betas import OAUTH_BETA_HEADER
from ...utils.cleanupRegistry import register_cleanup
from ...utils.debug import logForDebugging
from ...utils.settings.settingsCache import resetSettingsCache
from ...utils.userAgent import get_vivian_code_user_agent

_LOADING_PROMISE_TIMEOUT_MS = 30_000
_loading_complete_future: Optional[asyncio.Future[None]] = None
_SETTINGS_TIMEOUT_MS = 10.0
_DEFAULT_MAX_RETRIES = 5
_POLLING_INTERVAL_MS = 60 * 60 * 1000
_polling_task: Optional[asyncio.Task[None]] = None
_polling_task_unregister: Optional[Callable[[], None]] = None


def _resolve_loading_complete() -> None:
    future = _loading_complete_future
    if future is not None and not future.done():
        future.set_result(None)


def _invalidate_settings_cache() -> None:
    try:
        resetSettingsCache()
    except Exception:
        pass


def _retry_delay_ms(attempt: int) -> int:
    return min(1000 * (2 ** max(attempt - 1, 0)), 30_000)


def _get_remote_managed_settings_endpoint() -> str:
    return f"{get_oauth_config()['BASE_API_URL']}/api/vivian_code/settings"


def _get_remote_settings_auth_headers() -> tuple[dict[str, str], Optional[str]]:
    api_key = get_anthropic_api_key()
    if api_key:
        return ({"x-api-key": api_key}, None)

    oauth_tokens = get_vivian_ai_oauth_tokens()
    access_token = getattr(oauth_tokens, "access_token", None) or getattr(oauth_tokens, "accessToken", None)
    if access_token:
        return (
            {
                "Authorization": f"Bearer {access_token}",
                "anthropic-beta": OAUTH_BETA_HEADER,
            },
            None,
        )

    return ({}, "Authentication required for remote settings")


async def _fetch_remote_managed_settings(
    cached_checksum: Optional[str] = None,
    *,
    request_fn: Optional[Callable[..., Awaitable[httpx.Response]]] = None,
) -> RemoteManagedSettingsFetchResult:
    try:
        await check_and_refresh_oauth_token_if_needed()
    except Exception:
        pass

    auth_headers, auth_error = _get_remote_settings_auth_headers()
    if auth_error:
        return {
            "success": False,
            "error": auth_error,
            "skipRetry": True,
        }

    headers = {
        **auth_headers,
        "User-Agent": get_vivian_code_user_agent(),
    }
    if cached_checksum:
        headers["If-None-Match"] = f'"{cached_checksum}"'

    request = request_fn
    if request is None:
        async def _default_request(url: str, headers: dict[str, str]) -> httpx.Response:
            async with httpx.AsyncClient(timeout=_SETTINGS_TIMEOUT_MS) as client:
                return await client.get(url, headers=headers)

        request = _default_request

    try:
        response = await request(_get_remote_managed_settings_endpoint(), headers=headers)
    except httpx.TimeoutException:
        return {"success": False, "error": "Remote settings request timeout"}
    except httpx.HTTPError as error:
        return {"success": False, "error": str(error) or "Cannot connect to server"}

    if response.status_code == 304:
        logForDebugging("Remote settings: Using cached settings (304)")
        return {"success": True, "settings": None, "checksum": cached_checksum or ""}

    if response.status_code in {204, 404}:
        logForDebugging(f"Remote settings: No settings found ({response.status_code})")
        return {"success": True, "settings": {}, "checksum": ""}

    if response.status_code in {401, 403}:
        return {
            "success": False,
            "error": "Not authorized for remote settings",
            "skipRetry": True,
        }

    if response.status_code >= 400:
        return {
            "success": False,
            "error": f"Remote settings request failed ({response.status_code})",
        }

    try:
        payload = response.json()
    except ValueError:
        return {"success": False, "error": "Invalid remote settings format"}

    if not isinstance(payload, dict):
        return {"success": False, "error": "Invalid remote settings format"}

    settings = payload.get("settings")
    checksum = payload.get("checksum")
    if not isinstance(settings, dict):
        return {"success": False, "error": "Invalid settings structure"}
    if checksum is not None and not isinstance(checksum, str):
        return {"success": False, "error": "Invalid remote settings format"}

    logForDebugging("Remote settings: Fetched successfully")
    return {
        "success": True,
        "settings": settings,
        "checksum": checksum or computeChecksumFromSettings(settings),
    }


async def _fetch_with_retry(
    cached_checksum: Optional[str] = None,
    *,
    request_fn: Optional[Callable[..., Awaitable[httpx.Response]]] = None,
) -> RemoteManagedSettingsFetchResult:
    last_result: RemoteManagedSettingsFetchResult = {"success": False, "error": "Unknown error"}
    for attempt in range(1, _DEFAULT_MAX_RETRIES + 2):
        last_result = await _fetch_remote_managed_settings(
            cached_checksum,
            request_fn=request_fn,
        )
        if last_result.get("success"):
            return last_result
        if last_result.get("skipRetry"):
            return last_result
        if attempt > _DEFAULT_MAX_RETRIES:
            return last_result
        delay_ms = _retry_delay_ms(attempt)
        logForDebugging(
            f"Remote settings: Retry {attempt}/{_DEFAULT_MAX_RETRIES} after {delay_ms}ms"
        )
        await asyncio.sleep(delay_ms / 1000)
    return last_result


async def _save_settings(settings: dict[str, Any]) -> None:
    try:
        path = Path(getSettingsPath())
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        logForDebugging(f"Remote settings: Saved to {path}")
    except Exception as error:
        logForDebugging(f"Remote settings: Failed to save - {error}")


async def _fetch_and_load_remote_managed_settings(
    *,
    request_fn: Optional[Callable[..., Awaitable[httpx.Response]]] = None,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> Optional[dict[str, Any]]:
    if not isRemoteManagedSettingsEligible():
        return None

    cached_settings = getRemoteManagedSettingsSyncFromCache()
    cached_checksum = (
        computeChecksumFromSettings(cached_settings)
        if cached_settings
        else None
    )

    try:
        result = await _fetch_with_retry(cached_checksum, request_fn=request_fn)
        if not result.get("success"):
            if cached_settings is not None:
                logForDebugging("Remote settings: Using stale cache after fetch failure")
                setSessionCache(cached_settings)
                return cached_settings
            return None

        result_settings = result.get("settings")
        if result_settings is None and cached_settings is not None:
            logForDebugging("Remote settings: Cache still valid (304 Not Modified)")
            setSessionCache(cached_settings)
            return cached_settings

        new_settings = result_settings or {}
        if new_settings:
            security_result = checkManagedSettingsSecurity(
                cached_settings,
                new_settings,
                input_fn=input_fn,
                output_fn=output_fn,
            )
            if not handleSecurityCheckResult(security_result):
                logForDebugging(
                    "Remote settings: User rejected new settings, using cached settings"
                )
                return cached_settings

            setSessionCache(new_settings)
            await _save_settings(new_settings)
            _invalidate_settings_cache()
            logForDebugging("Remote settings: Applied new settings successfully")
            return new_settings

        setSessionCache({})
        try:
            os.unlink(getSettingsPath())
            logForDebugging("Remote settings: Deleted cached file (empty response)")
        except OSError:
            pass
        _invalidate_settings_cache()
        return {}
    except Exception:
        if cached_settings is not None:
            logForDebugging("Remote settings: Using stale cache after error")
            setSessionCache(cached_settings)
            return cached_settings
        return None


async def _poll_remote_settings() -> None:
    if not isRemoteManagedSettingsEligible():
        return
    previous_cache = getRemoteManagedSettingsSyncFromCache()
    previous_text = json.dumps(previous_cache, sort_keys=True) if previous_cache is not None else None
    try:
        await _fetch_and_load_remote_managed_settings()
        current_cache = getRemoteManagedSettingsSyncFromCache()
        current_text = json.dumps(current_cache, sort_keys=True) if current_cache is not None else None
        if current_text != previous_text:
            _invalidate_settings_cache()
    except Exception:
        pass


async def _background_poll_loop() -> None:
    try:
        while True:
            await asyncio.sleep(_POLLING_INTERVAL_MS / 1000)
            await _poll_remote_settings()
    except asyncio.CancelledError:
        raise


def initializeRemoteManagedSettingsLoadingPromise() -> None:
    """Initialize the remote managed settings loading.

    Mirrors initializeRemoteManagedSettingsLoadingPromise() from index.ts.
    """
    global _loading_complete_future
    if _loading_complete_future is not None:
        return
    if not isEligibleForRemoteManagedSettings():
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    _loading_complete_future = loop.create_future()

    async def _timeout_resolve() -> None:
        await asyncio.sleep(_LOADING_PROMISE_TIMEOUT_MS / 1000)
        _resolve_loading_complete()

    loop.create_task(_timeout_resolve())


def computeChecksumFromSettings(settings: dict) -> str:
    """Compute a checksum from a settings dict.

    Mirrors computeChecksumFromSettings() from index.ts.
    """
    data = json.dumps(settings, sort_keys=True, separators=(",", ":"), default=str)
    return f"sha256:{hashlib.sha256(data.encode()).hexdigest()}"


def isEligibleForRemoteManagedSettings() -> bool:
    """Check if eligible for remote managed settings.

    Mirrors isEligibleForRemoteManagedSettings() from index.ts.
    """
    return isRemoteManagedSettingsEligible()


async def waitForRemoteManagedSettingsToLoad() -> None:
    """Wait for remote managed settings to load.

    Mirrors waitForRemoteManagedSettingsToLoad() from index.ts.
    """
    if _loading_complete_future is not None:
        await _loading_complete_future


async def clearRemoteManagedSettingsCache() -> None:
    """Clear the remote managed settings cache.

    Mirrors clearRemoteManagedSettingsCache() from index.ts.
    """
    global _loading_complete_future
    _resolve_loading_complete()
    _loading_complete_future = None
    stopBackgroundPolling()
    resetSyncCache()

    try:
        os.unlink(getSettingsPath())
    except OSError:
        pass

    _invalidate_settings_cache()


async def loadRemoteManagedSettings(
    *,
    request_fn: Optional[Callable[..., Awaitable[httpx.Response]]] = None,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> None:
    global _loading_complete_future

    if isRemoteManagedSettingsEligible() and _loading_complete_future is None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        _loading_complete_future = loop.create_future()

    if getRemoteManagedSettingsSyncFromCache() is not None:
        _resolve_loading_complete()

    try:
        settings = await _fetch_and_load_remote_managed_settings(
            request_fn=request_fn,
            input_fn=input_fn,
            output_fn=output_fn,
        )
        if isRemoteManagedSettingsEligible():
            startBackgroundPolling()
        if settings is not None:
            _invalidate_settings_cache()
    finally:
        _resolve_loading_complete()


async def refreshRemoteManagedSettings(
    *,
    request_fn: Optional[Callable[..., Awaitable[httpx.Response]]] = None,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> None:
    await clearRemoteManagedSettingsCache()
    if not isRemoteManagedSettingsEligible():
        _invalidate_settings_cache()
        return
    await _fetch_and_load_remote_managed_settings(
        request_fn=request_fn,
        input_fn=input_fn,
        output_fn=output_fn,
    )
    logForDebugging("Remote settings: Refreshed after auth change")
    _invalidate_settings_cache()


def startBackgroundPolling() -> None:
    global _polling_task, _polling_task_unregister
    if _polling_task is not None and not _polling_task.done():
        return
    if not isRemoteManagedSettingsEligible():
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    _polling_task = loop.create_task(_background_poll_loop())
    if _polling_task_unregister is None:
        async def _cleanup() -> None:
            stopBackgroundPolling()

        _polling_task_unregister = register_cleanup(_cleanup)


def stopBackgroundPolling() -> None:
    global _polling_task, _polling_task_unregister
    if _polling_task is not None:
        _polling_task.cancel()
        _polling_task = None
    if _polling_task_unregister is not None:
        _polling_task_unregister()
        _polling_task_unregister = None


initialize_remote_managed_settings_loading_promise = initializeRemoteManagedSettingsLoadingPromise
compute_checksum_from_settings = computeChecksumFromSettings
is_eligible_for_remote_managed_settings = isEligibleForRemoteManagedSettings
wait_for_remote_managed_settings_to_load = waitForRemoteManagedSettingsToLoad
clear_remote_managed_settings_cache = clearRemoteManagedSettingsCache
load_remote_managed_settings = loadRemoteManagedSettings
refresh_remote_managed_settings = refreshRemoteManagedSettings
start_background_polling = startBackgroundPolling
stop_background_polling = stopBackgroundPolling
