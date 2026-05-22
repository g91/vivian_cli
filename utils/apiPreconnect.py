"""Port of src/utils/apiPreconnect.ts."""
from __future__ import annotations

import os
import urllib.request

_fired = False


async def preconnectAnthropicApi():
    global _fired
    if _fired:
        return None
    _fired = True

    try:
        from .envUtils import is_env_truthy
    except Exception:
        def is_env_truthy(value):
            return bool(value)

    if (
        is_env_truthy(os.environ.get("vivian_CODE_USE_BEDROCK"))
        or is_env_truthy(os.environ.get("vivian_CODE_USE_VERTEX"))
        or is_env_truthy(os.environ.get("vivian_CODE_USE_FOUNDRY"))
    ):
        return None

    if any(
        os.environ.get(name)
        for name in (
            "HTTPS_PROXY",
            "https_proxy",
            "HTTP_PROXY",
            "http_proxy",
            "ANTHROPIC_UNIX_SOCKET",
            "vivian_CODE_CLIENT_CERT",
            "vivian_CODE_CLIENT_KEY",
        )
    ):
        return None

    try:
        from ..constants.oauth import get_oauth_config

        base_url = os.environ.get("ANTHROPIC_BASE_URL") or get_oauth_config()["BASE_API_URL"]
    except Exception:
        base_url = os.environ.get("ANTHROPIC_BASE_URL") or "https://api.anthropic.com"

    request = urllib.request.Request(base_url, method="HEAD")
    try:
        urllib.request.urlopen(request, timeout=10).read(0)
    except Exception:
        return None
    return None


preconnect_anthropic_api = preconnectAnthropicApi
