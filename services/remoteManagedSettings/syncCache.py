"""Eligibility check for remote managed settings.

Mirrors src/services/remoteManagedSettings/syncCache.ts.
"""
from __future__ import annotations

import os
from typing import Optional

from ...services.oauth.client import shouldUsevivianAIAuth
from ...utils.auth import get_anthropic_api_key, get_vivian_ai_oauth_tokens
from ...utils.model.providers import getAPIProvider, isFirstPartyAnthropicBaseUrl
from .syncCacheState import resetSyncCache as resetLeafCache, setEligibility


_cached: Optional[bool] = None


def resetSyncCache() -> None:
    global _cached
    _cached = None
    resetLeafCache()


def _token_access_token(tokens: object | None) -> Optional[str]:
    if tokens is None:
        return None
    return getattr(tokens, "access_token", None) or getattr(tokens, "accessToken", None)


def _token_subscription_type(tokens: object | None) -> Optional[str]:
    if tokens is None:
        return None
    return getattr(tokens, "subscription_type", None) or getattr(tokens, "subscriptionType", None)


def _token_scopes(tokens: object | None) -> list[str]:
    if tokens is None:
        return []
    scopes = getattr(tokens, "scopes", None)
    if isinstance(scopes, (list, tuple)):
        return [str(scope) for scope in scopes]
    return []


def isRemoteManagedSettingsEligible() -> bool:
    global _cached
    if _cached is not None:
        return _cached

    if getAPIProvider() != "firstParty":
        _cached = setEligibility(False)
        return _cached

    if not isFirstPartyAnthropicBaseUrl():
        _cached = setEligibility(False)
        return _cached

    if os.environ.get("vivian_CODE_ENTRYPOINT") == "local-agent":
        _cached = setEligibility(False)
        return _cached

    tokens = get_vivian_ai_oauth_tokens()
    access_token = _token_access_token(tokens)
    subscription_type = _token_subscription_type(tokens)

    if access_token and subscription_type is None:
        _cached = setEligibility(True)
        return _cached

    if access_token and shouldUsevivianAIAuth(_token_scopes(tokens)) and subscription_type in {"enterprise", "team"}:
        _cached = setEligibility(True)
        return _cached

    if get_anthropic_api_key():
        _cached = setEligibility(True)
        return _cached

    _cached = setEligibility(False)
    return _cached


reset_sync_cache = resetSyncCache
is_remote_managed_settings_eligible = isRemoteManagedSettingsEligible