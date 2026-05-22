"""Usage API — mirrors src/services/api/usage.ts."""
from __future__ import annotations

from typing import Optional


class RateLimit:
    def __init__(self, utilization: Optional[float], resets_at: Optional[str]) -> None:
        self.utilization = utilization
        self.resets_at = resets_at


class ExtraUsage:
    def __init__(
        self,
        is_enabled: bool,
        monthly_limit: Optional[float],
        used_credits: Optional[float],
        utilization: Optional[float],
    ) -> None:
        self.is_enabled = is_enabled
        self.monthly_limit = monthly_limit
        self.used_credits = used_credits
        self.utilization = utilization


Utilization = dict  # {five_hour?, seven_day?, seven_day_opus?, ..., extra_usage?}


async def fetchUtilization() -> Optional[Utilization]:
    """Fetch rate limit utilization from the API.

    Mirrors fetchUtilization() from usage.ts.
    """
    try:
        from ...utils.auth import isvivianAISubscriber, hasProfileScope, getvivianAIOAuthTokens
        if not isvivianAISubscriber() or not hasProfileScope():
            return {}

        from ..oauth.client import isOAuthTokenExpired
        tokens = getvivianAIOAuthTokens()
        if tokens and isOAuthTokenExpired(tokens.get("expiresAt")):
            return None

        from ...utils.http import get_auth_headers
        auth = get_auth_headers()
        if auth.get("error"):
            raise Exception(f"Auth error: {auth['error']}")

        from ...constants.oauth import get_oauth_config
        import json
        import urllib.request

        oauth_config = get_oauth_config()
        url = f"{oauth_config['BASE_API_URL']}/api/oauth/usage"
        req = urllib.request.Request(
            url,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "vivianCode/Python",
                **auth.get("headers", {}),
            },
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


fetch_utilization = fetchUtilization
