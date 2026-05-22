"""Port of src/bridge/bridgeConfig.ts

Shared bridge auth/URL resolution. Consolidates ant-only vivian_BRIDGE_*
dev overrides previously copy-pasted across a dozen files.
"""
from __future__ import annotations

import os
from typing import Optional


def getBridgeTokenOverride() -> Optional[str]:
    """Ant-only dev override: vivian_BRIDGE_OAUTH_TOKEN, else None."""
    if os.environ.get("USER_TYPE") == "ant":
        return os.environ.get("vivian_BRIDGE_OAUTH_TOKEN") or None
    return None


def getBridgeBaseUrlOverride() -> Optional[str]:
    """Ant-only dev override: vivian_BRIDGE_BASE_URL, else None."""
    if os.environ.get("USER_TYPE") == "ant":
        return os.environ.get("vivian_BRIDGE_BASE_URL") or None
    return None


def getBridgeAccessToken() -> Optional[str]:
    """Access token for bridge API calls: dev override first, then OAuth keychain."""
    override = getBridgeTokenOverride()
    if override:
        return override
    try:
        from ..utils.auth import get_vivian_ai_oauth_tokens
        tokens = get_vivian_ai_oauth_tokens()
        return tokens.get("accessToken") if tokens else None
    except Exception:
        return None


def getBridgeBaseUrl() -> str:
    """Base URL for bridge API calls: dev override first, then production OAuth config."""
    override = getBridgeBaseUrlOverride()
    if override:
        return override
    try:
        from ..constants.oauth import get_oauth_config
        return get_oauth_config()["BASE_API_URL"]
    except Exception:
        return "https://api-vivian.d0a.net"
