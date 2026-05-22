"""OAuth / API configuration constants for Vivian.

All values resolve against https://api-vivian.d0a.net.
Override any field via environment variables.
"""
from __future__ import annotations

import os
from typing import Optional

_BASE_API_URL = os.environ.get("VIVIAN_API_BASE_URL", "https://api-vivian.d0a.net")
_vivian_AI_URL = os.environ.get("VIVIAN_WEB_URL", "https://vivian.d0a.net")

# OAuth 2.0 PKCE config
_OAUTH_CLIENT_ID = os.environ.get("VIVIAN_OAUTH_CLIENT_ID", "vivian-cli")
_OAUTH_SCOPES = "openid profile email offline_access"

_OAUTH_CONFIG: Optional[dict] = None


def get_oauth_config() -> dict:
    """Return the current OAuth / API config dict.

    All bridge modules read this via:
        from ..constants.oauth import get_oauth_config
        cfg = get_oauth_config()
        base = cfg["BASE_API_URL"]
    """
    global _OAUTH_CONFIG
    if _OAUTH_CONFIG is not None:
        return _OAUTH_CONFIG

    _OAUTH_CONFIG = {
        # REST API base — all /v1/* calls go here
        "BASE_API_URL": _BASE_API_URL,

        # Web UI base — session URLs, OAuth redirects
        "vivian_AI_URL": _vivian_AI_URL,

        # OAuth / PKCE
        "CLIENT_ID": _OAUTH_CLIENT_ID,
        "SCOPES": _OAUTH_SCOPES,
        "REDIRECT_URI": f"{_vivian_AI_URL}/oauth/callback",

        # Token endpoints
        "TOKEN_URL": f"{_BASE_API_URL}/oauth/token",
        "REVOKE_URL": f"{_BASE_API_URL}/oauth/revoke",
        "USERINFO_URL": f"{_BASE_API_URL}/oauth/userinfo",
        "AUTHORIZE_URL": f"{_vivian_AI_URL}/oauth/authorize",

        # Keychain service name for persisting tokens
        "KEYCHAIN_SERVICE": "vivian-cli",
        "KEYCHAIN_ACCOUNT": "oauth-token",
    }
    return _OAUTH_CONFIG


def set_oauth_config(overrides: dict) -> None:
    """Merge overrides into the OAuth config (used by integration layer)."""
    global _OAUTH_CONFIG
    base = get_oauth_config()
    _OAUTH_CONFIG = {**base, **overrides}


def get_base_api_url() -> str:
    return get_oauth_config()["BASE_API_URL"]


def get_web_url() -> str:
    return get_oauth_config()["vivian_AI_URL"]
