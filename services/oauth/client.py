"""OAuth client — mirrors src/services/oauth/client.ts."""
from __future__ import annotations

from dataclasses import asdict
from typing import Optional


def shouldUsevivianAIAuth(scopes: Optional[list[str]]) -> bool:
    """Check if user has Vivian AI auth scope.

    Mirrors shouldUsevivianAIAuth() from client.ts.
    """
    if not scopes:
        return False
    from ...constants.oauth import vivian_AI_INFERENCE_SCOPE
    return vivian_AI_INFERENCE_SCOPE in scopes


def parseScopes(scope_string: Optional[str]) -> list[str]:
    """Parse a space-separated scope string into a list.

    Mirrors parseScopes() from client.ts.
    """
    if not scope_string:
        return []
    return [s for s in scope_string.split(" ") if s]


def buildAuthUrl(
    code_challenge: str,
    state: str,
    port: int,
    is_manual: bool = False,
    login_with_vivian_ai: bool = False,
    inference_only: bool = False,
    org_uuid: Optional[str] = None,
    login_hint: Optional[str] = None,
    login_method: Optional[str] = None,
) -> str:
    """Build OAuth authorization URL.

    Mirrors buildAuthUrl() from client.ts.
    """
    try:
        from ...constants.oauth import get_oauth_config
        config = get_oauth_config()
    except Exception:
        return ""

    params = {
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "response_type": "code",
        "client_id": config.get("CLIENT_ID", ""),
        "redirect_uri": f"http://localhost:{port}/callback",
        "state": state,
    }
    if scopes := config.get("SCOPES"):
        params["scope"] = scopes
    if login_with_vivian_ai:
        params["login_with_vivian_ai"] = "true"
    if inference_only:
        params["inference_only"] = "true"
    if is_manual:
        params["manual"] = "true"
    if org_uuid:
        params["organization_uuid"] = org_uuid
    if login_hint:
        params["login_hint"] = login_hint
    if login_method:
        params["login_method"] = login_method

    from urllib.parse import urlencode
    return f"{config.get('AUTHORIZE_URL', '')}?{urlencode(params)}"


def isOAuthTokenExpired(expires_at: Optional[int]) -> bool:
    """Check if an OAuth token is expired.

    Mirrors isOAuthTokenExpired() from client.ts.
    """
    if expires_at is None:
        return True
    import time
    return expires_at < time.time() * 1000


async def exchangeCodeForTokens(code: str, code_verifier: str, port: int) -> dict:
    """Exchange authorization code for tokens.

    Mirrors exchangeCodeForTokens() from client.ts.
    """
    del port
    from ...integration.oauth_manager import get_oauth_manager

    token_set = await __import__("asyncio").to_thread(
        get_oauth_manager().complete_pkce_login,
        code,
        code_verifier,
    )
    return asdict(token_set)


async def refreshOAuthToken(refresh_token: str) -> dict:
    """Refresh an OAuth token.

    Mirrors refreshOAuthToken() from client.ts.
    """
    from ...integration.oauth_manager import get_oauth_manager

    manager = get_oauth_manager()
    token_set = manager.get_tokens()
    if token_set is None or token_set.refresh_token != refresh_token:
        return {}
    token_set.expires_at = 0
    refreshed = await manager.refresh_if_needed()
    updated = manager.get_tokens()
    if not refreshed or updated is None:
        return {}
    return asdict(updated)


async def fetchAndStoreUserRoles(access_token: str) -> Optional[dict]:
    """Fetch and store user roles.

    Mirrors fetchAndStoreUserRoles() from client.ts.
    """
    return await fetchProfileInfo(access_token)


async def fetchProfileInfo(access_token: str) -> dict:
    """Fetch profile info for the given access token.

    Mirrors fetchProfileInfo() from client.ts.
    """
    del access_token
    from ...integration.oauth_manager import get_oauth_manager

    info = await get_oauth_manager().fetch_userinfo()
    return info or {}


async def getOrganizationUUID() -> Optional[str]:
    """Get the organization UUID.

    Mirrors getOrganizationUUID() from client.ts.
    """
    try:
        from ...utils.auth import get_organization_uuid

        return get_organization_uuid()
    except Exception:
        return None


async def populateOAuthAccountInfoIfNeeded() -> bool:
    """Populate OAuth account info if not already done.

    Mirrors populateOAuthAccountInfoIfNeeded() from client.ts.
    """
    from ...integration.oauth_manager import get_oauth_manager

    manager = get_oauth_manager()
    token_set = manager.get_tokens()
    if token_set is None or not token_set.access_token:
        return False
    if token_set.email and token_set.organization_uuid:
        return False
    info = await manager.fetch_userinfo()
    return bool(info)


def storeOAuthAccountInfo(info: dict) -> None:
    """Store OAuth account info.

    Mirrors storeOAuthAccountInfo() from client.ts.
    """
    from ...integration.oauth_manager import TokenSet, get_oauth_manager

    manager = get_oauth_manager()
    token_set = manager.get_tokens()
    if token_set is None:
        access_token = info.get("access_token")
        if not access_token:
            return
        token_set = TokenSet(access_token=access_token)
    token_set.account_uuid = info.get("sub") or info.get("account_uuid") or token_set.account_uuid
    token_set.organization_uuid = info.get("organization_uuid") or info.get("org_id") or token_set.organization_uuid
    token_set.email = info.get("email") or token_set.email
    manager.set_tokens(token_set)


should_use_vivian_ai_auth = shouldUsevivianAIAuth
parse_scopes = parseScopes
build_auth_url = buildAuthUrl
is_oauth_token_expired = isOAuthTokenExpired
exchange_code_for_tokens = exchangeCodeForTokens
refresh_oauth_token = refreshOAuthToken
fetch_and_store_user_roles = fetchAndStoreUserRoles
fetch_profile_info = fetchProfileInfo
get_organization_uuid = getOrganizationUUID
populate_oauth_account_info_if_needed = populateOAuthAccountInfoIfNeeded
store_oauth_account_info = storeOAuthAccountInfo
