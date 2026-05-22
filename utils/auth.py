"""Authentication utilities — mirrors src/utils/auth.ts.

All auth state is sourced from OAuthManager (integration.oauth_manager).

Priority for API key / access token:
  1. VIVIAN_API_KEY env var
  2. ANTHROPIC_API_KEY env var (legacy compat)
  3. VIVIAN_ACCESS_TOKEN / vivian_BRIDGE_OAUTH_TOKEN env vars (OAuth)
  4. Token persisted in ~/.config/vivian/tokens.json
"""
from __future__ import annotations
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


def _oauth() -> Optional[object]:
    """Return the OAuthManager instance, or None if integration isn't set up."""
    try:
        from ..integration.oauth_manager import get_oauth_manager
        return get_oauth_manager()
    except Exception:
        return None


def get_anthropic_api_key() -> Optional[str]:
    """Return the best available API key / access token."""
    return (
        os.environ.get("VIVIAN_API_KEY")
        or os.environ.get("ANTHROPIC_API_KEY")
        or (_oauth() and _oauth().get_access_token())
    )


def has_api_key() -> bool:
    return bool(get_anthropic_api_key())


def get_auth_token_source() -> dict:
    """Describe how the current API token was obtained."""
    if os.environ.get("VIVIAN_API_KEY"):
        return {"has_token": True, "source": "env_vivian"}
    if os.environ.get("ANTHROPIC_API_KEY"):
        return {"has_token": True, "source": "env_anthropic"}
    om = _oauth()
    if om:
        ts = om.get_tokens()
        if ts and ts.access_token:
            src = "oauth_env" if os.environ.get("VIVIAN_ACCESS_TOKEN") or os.environ.get("vivian_BRIDGE_OAUTH_TOKEN") else "oauth_disk"
            return {"has_token": True, "source": src, "email": ts.email, "org": ts.organization_uuid}
    return {"has_token": False, "source": None}


def get_vivian_ai_oauth_tokens() -> Optional[object]:
    """Return the live TokenSet, or None if not authenticated via OAuth."""
    om = _oauth()
    return om.get_tokens() if om else None


def get_organization_uuid() -> Optional[str]:
    om = _oauth()
    return om.get_organization_uuid() if om else None


def is_vivian_ai_subscriber() -> bool:
    """True when the user is authenticated (any method)."""
    return bool(get_anthropic_api_key())


def get_subscription_type() -> Optional[str]:
    ts = get_vivian_ai_oauth_tokens()
    if ts:
        return getattr(ts, "subscription_type", "vivian_member")
    return "api_key" if has_api_key() else None


def get_rate_limit_tier() -> Optional[str]:
    return None  # Vivian backend manages rate limits server-side


async def check_and_refresh_oauth_token_if_needed() -> bool:
    """Proactively refresh the OAuth token if it's about to expire."""
    om = _oauth()
    if om is None:
        return False
    return await om.refresh_if_needed()


async def handle_oauth_401_error() -> bool:
    """Called after receiving 401. Attempts a token refresh. Returns True if refreshed."""
    om = _oauth()
    if om is None:
        return False
    ts = om.get_tokens()
    if ts and ts.refresh_token:
        ts.expires_at = 0  # Force refresh
        return await om.refresh_if_needed()
    return False
