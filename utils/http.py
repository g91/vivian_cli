"""HTTP utility constants and helpers — mirrors src/utils/http.ts."""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional
import os


AuthHeaders = Dict[str, Any]


def getUserAgent():
    try:
        from .userAgent import get_vivian_code_user_agent
        from .workloadContext import get_workload
    except Exception:
        entrypoint = os.environ.get("vivian_CODE_ENTRYPOINT") or "cli"
        user_type = os.environ.get("USER_TYPE") or "external"
        return f"vivian-cli/0.0.0 ({user_type}, {entrypoint})"

    agent_sdk_version = os.environ.get("vivian_AGENT_SDK_VERSION")
    client_app = os.environ.get("vivian_AGENT_SDK_CLIENT_APP")
    user_type = os.environ.get("USER_TYPE") or "external"
    entrypoint = os.environ.get("vivian_CODE_ENTRYPOINT") or "cli"
    workload = get_workload()

    suffixes = [f"{user_type}, {entrypoint}"]
    if agent_sdk_version:
        suffixes.append(f"agent-sdk/{agent_sdk_version}")
    if client_app:
        suffixes.append(f"client-app/{client_app}")
    if workload:
        suffixes.append(f"workload/{workload}")
    return f"vivian-cli/{get_vivian_code_user_agent().split('/', 1)[-1]} ({', '.join(suffixes)})"


def getMCPUserAgent():
    try:
        from .userAgent import get_vivian_code_user_agent
        version = get_vivian_code_user_agent().split("/", 1)[-1]
    except Exception:
        version = "0.0.0"

    parts: list[str] = []
    if os.environ.get("vivian_CODE_ENTRYPOINT"):
        parts.append(os.environ["vivian_CODE_ENTRYPOINT"])
    if os.environ.get("vivian_AGENT_SDK_VERSION"):
        parts.append(f"agent-sdk/{os.environ['vivian_AGENT_SDK_VERSION']}")
    if os.environ.get("vivian_AGENT_SDK_CLIENT_APP"):
        parts.append(f"client-app/{os.environ['vivian_AGENT_SDK_CLIENT_APP']}")
    suffix = f" ({', '.join(parts)})" if parts else ""
    return f"vivian-code/{version}{suffix}"


def getWebFetchUserAgent():
    try:
        from .userAgent import get_vivian_code_user_agent
        base = get_vivian_code_user_agent()
    except Exception:
        base = "vivian-cli/0.0.0"
    return f"vivian-User ({base}; +https://api-vivian.d0a.net/support)"


def getAuthHeaders():
    """Get authentication headers for API requests"""
    try:
        from .auth import get_anthropic_api_key, get_vivian_ai_oauth_tokens, is_vivian_ai_subscriber
        from .betas import OAUTH_BETA_HEADER
    except Exception:
        return {"headers": {}, "error": "Authentication helpers unavailable"}

    if is_vivian_ai_subscriber():
        oauth_tokens = get_vivian_ai_oauth_tokens()
        access_token = getattr(oauth_tokens, "access_token", None) if oauth_tokens is not None else None
        if access_token:
            return {
                "headers": {
                    "Authorization": f"Bearer {access_token}",
                    "anthropic-beta": OAUTH_BETA_HEADER,
                }
            }

    api_key = get_anthropic_api_key()
    if api_key:
        return {"headers": {"x-api-key": api_key}}
    return {"headers": {}, "error": "No API key available"}


async def withOAuth401Retry(request: Optional[Callable[[], Any]] = None, opts: Optional[dict] = None):
    """Wrapper that handles OAuth 401 errors by force-refreshing the token and"""
    if request is None:
        return None

    try:
        return await request()
    except Exception as err:
        status = getattr(err, "status", None)
        response = getattr(err, "response", None)
        if status is None and response is not None:
            status = getattr(response, "status", None)
        response_data = getattr(response, "data", None)
        is_auth_error = status == 401 or (
            bool(opts and opts.get("also403Revoked"))
            and status == 403
            and isinstance(response_data, str)
            and "OAuth token has been revoked" in response_data
        )
        if not is_auth_error:
            raise

        try:
            from .auth import handle_oauth_401_error
        except Exception:
            raise

        refreshed = await handle_oauth_401_error()
        if not refreshed:
            raise
        return await request()


get_user_agent = getUserAgent
get_mcp_user_agent = getMCPUserAgent
get_web_fetch_user_agent = getWebFetchUserAgent
get_auth_headers = getAuthHeaders
with_oauth_401_retry = withOAuth401Retry

