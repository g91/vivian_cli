"""Port of src/bridge/trustedDevice.ts

Trusted device token source for bridge (remote-control) sessions.
Bridge sessions have SecurityTier=ELEVATED on the server (CCR v2).
"""
from __future__ import annotations

import functools
import os
import socket
import sys
from typing import Optional


_TRUSTED_DEVICE_GATE = "tengu_sessions_elevated_auth_enforcement"


def _is_gate_enabled() -> bool:
    try:
        from ..services.analytics.growthbook import get_feature_value_cached_may_be_stale
        return bool(get_feature_value_cached_may_be_stale(_TRUSTED_DEVICE_GATE, False))
    except Exception:
        return False


@functools.lru_cache(maxsize=1)
def _read_stored_token() -> Optional[str]:
    """Memoized read of the trusted device token from env or secure storage."""
    env_token = os.environ.get("vivian_TRUSTED_DEVICE_TOKEN")
    if env_token:
        return env_token
    try:
        from ..utils.secure_storage import get_secure_storage
        data = get_secure_storage().read()
        return data.get("trustedDeviceToken") if data else None
    except Exception:
        return None


def getTrustedDeviceToken() -> Optional[str]:
    if not _is_gate_enabled():
        return None
    return _read_stored_token()


def clearTrustedDeviceTokenCache() -> None:
    _read_stored_token.cache_clear()


def clearTrustedDeviceToken() -> None:
    if not _is_gate_enabled():
        return
    try:
        from ..utils.secure_storage import get_secure_storage
        storage = get_secure_storage()
        data = storage.read()
        if data and "trustedDeviceToken" in data:
            del data["trustedDeviceToken"]
            storage.update(data)
    except Exception:
        pass
    _read_stored_token.cache_clear()


async def enrollTrustedDevice() -> None:
    """
    Enroll this device via POST /auth/trusted_devices and persist the token
    to keychain. Best-effort — logs and returns on failure.
    """
    try:
        try:
            from ..services.analytics.growthbook import check_gate_cached_or_blocking
            if not (await check_gate_cached_or_blocking(_TRUSTED_DEVICE_GATE)):
                return
        except Exception:
            return

        if os.environ.get("vivian_TRUSTED_DEVICE_TOKEN"):
            return

        try:
            from ..utils.auth import get_vivian_ai_oauth_tokens
            tokens = get_vivian_ai_oauth_tokens()
            access_token = tokens.get("accessToken") if tokens else None
        except Exception:
            return

        if not access_token:
            return

        try:
            from ..utils.privacy_level import is_essential_traffic_only
            if is_essential_traffic_only():
                return
        except Exception:
            pass

        try:
            from ..constants.oauth import get_oauth_config
            base_url = get_oauth_config()["BASE_API_URL"]
        except Exception:
            return

        hostname = socket.gethostname()
        platform = sys.platform

        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{base_url}/api/auth/trusted_devices",
                json={"display_name": f"vivian Code on {hostname} · {platform}"},
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
            )
            if resp.status_code not in (200, 201):
                return
            data = resp.json()

        token = data.get("device_token")
        if not isinstance(token, str) or not token:
            return

        try:
            from ..utils.secure_storage import get_secure_storage
            storage = get_secure_storage()
            storage_data = storage.read()
            if not storage_data:
                return
            storage_data["trustedDeviceToken"] = token
            storage.update(storage_data)
            _read_stored_token.cache_clear()
        except Exception:
            pass

    except Exception:
        pass
