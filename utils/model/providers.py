"""Port of src/utils/model/providers.ts"""
from __future__ import annotations

import os
from typing import Literal

APIProvider = Literal['firstParty', 'bedrock', 'vertex', 'foundry']

def _is_env_truthy(val: str | None) -> bool:
    if not val:
        return False
    return val.strip().lower() not in ('0', 'false', 'no', '')

def getAPIProvider() -> APIProvider:
    if _is_env_truthy(os.environ.get('vivian_CODE_USE_BEDROCK')):
        return 'bedrock'
    if _is_env_truthy(os.environ.get('vivian_CODE_USE_VERTEX')):
        return 'vertex'
    if _is_env_truthy(os.environ.get('vivian_CODE_USE_FOUNDRY')):
        return 'foundry'
    return 'firstParty'

def isFirstPartyAnthropicBaseUrl() -> bool:
    base_url = os.environ.get('ANTHROPIC_BASE_URL')
    if not base_url:
        return True
    try:
        from urllib.parse import urlparse
        host = urlparse(base_url).hostname or ''
        allowed = ['api-vivian.d0a.net']
        if os.environ.get('USER_TYPE') == 'ant':
            allowed.append('api-staging-vivian.d0a.net')
        return host in allowed
    except Exception:
        return False
