"""Product constants — mirrors src/constants/product.ts."""
from __future__ import annotations

PRODUCT_URL = "https://api-vivian.d0a.net/vivian-code"

vivian_AI_BASE_URL = "https://api-vivian.d0a.net"
vivian_AI_STAGING_BASE_URL = "https://api-vivian.d0a.net"
vivian_AI_LOCAL_BASE_URL = "http://localhost:4000"


def isRemoteSessionStaging(session_id: str = "", ingress_url: str = "") -> bool:
    """Determine if we're in a staging environment for remote sessions."""
    return "_staging_" in (session_id or "") or "staging" in (ingress_url or "")


def isRemoteSessionLocal(session_id: str = "", ingress_url: str = "") -> bool:
    """Determine if we're in a local-dev environment for remote sessions."""
    return "_local_" in (session_id or "") or "localhost" in (ingress_url or "")


def getvivianAiBaseUrl(session_id: str = "", ingress_url: str = "") -> str:
    """Get the base URL for vivian AI based on environment."""
    if isRemoteSessionLocal(session_id, ingress_url):
        return vivian_AI_LOCAL_BASE_URL
    if isRemoteSessionStaging(session_id, ingress_url):
        return vivian_AI_STAGING_BASE_URL
    return vivian_AI_BASE_URL


def getRemoteSessionUrl(session_id: str, ingress_url: str = "") -> str:
    """Get the full session URL for a remote session."""
    from ..bridge.sessionIdCompat import toCompatSessionId
    compat_id = toCompatSessionId(session_id)
    base_url = getvivianAiBaseUrl(compat_id, ingress_url)
    return f"{base_url}/code/{compat_id}"


is_remote_session_staging = isRemoteSessionStaging
is_remote_session_local = isRemoteSessionLocal
get_vivian_ai_base_url = getvivianAiBaseUrl
get_remote_session_url = getRemoteSessionUrl
