"""User metadata helpers for analytics and GrowthBook."""
from __future__ import annotations

import asyncio
import os
from functools import lru_cache
from typing import Any, Dict

from .. import __version__
from ..bootstrap.state import getSessionId
from ..constants.system import getCwd
from .auth import get_rate_limit_tier, get_subscription_type
from .config import get_global_config, get_or_create_user_id
from .env import getHostPlatformForAnalytics
from .envUtils import is_env_truthy
from .execFileNoThrow import exec_file_no_throw


GitHubActionsMetadata = Dict[str, Any]
CoreUserData = Dict[str, Any]

_EMAIL_NOT_FETCHED = object()
cachedEmail: str | None | object = _EMAIL_NOT_FETCHED
emailFetchPromise: asyncio.Task | None = None


def _get_oauth_account_info() -> dict[str, Any] | None:
    try:
        from .auth import getOauthAccountInfo  # type: ignore

        info = getOauthAccountInfo()
        return info if isinstance(info, dict) else None
    except Exception:
        pass

    try:
        from .auth import get_vivian_ai_oauth_tokens

        tokens = get_vivian_ai_oauth_tokens()
        if tokens is None:
            cfg = get_global_config() or {}
            info = cfg.get('oauthAccount')
            return info if isinstance(info, dict) else None
        return {
            'organizationUuid': getattr(tokens, 'organization_uuid', None),
            'accountUuid': getattr(tokens, 'account_uuid', None),
            'emailAddress': getattr(tokens, 'email', None),
        }
    except Exception:
        cfg = get_global_config() or {}
        info = cfg.get('oauthAccount')
        return info if isinstance(info, dict) else None


@lru_cache(maxsize=None)
def getCoreUserData(includeAnalyticsMetadata: bool = False) -> CoreUserData:
    device_id = get_or_create_user_id()
    config = get_global_config() or {}
    subscription_type: str | None = None
    rate_limit_tier: str | None = None
    first_token_time: int | None = None

    if includeAnalyticsMetadata:
        try:
            subscription_type = get_subscription_type()
        except Exception:
            subscription_type = None
        try:
            rate_limit_tier = get_rate_limit_tier()
        except Exception:
            rate_limit_tier = None
        if subscription_type and config.get('vivianCodeFirstTokenDate'):
            try:
                import datetime as _dt

                first_token_time = int(
                    _dt.datetime.fromisoformat(
                        str(config['vivianCodeFirstTokenDate']).replace('Z', '+00:00')
                    ).timestamp()
                    * 1000
                )
            except Exception:
                first_token_time = None

    oauth_account = _get_oauth_account_info() or {}
    result: CoreUserData = {
        'deviceId': device_id,
        'sessionId': getSessionId(),
        'email': getEmail(),
        'appVersion': os.environ.get('vivian_CODE_VERSION') or os.environ.get('VIVIAN_VERSION') or __version__,
        'platform': getHostPlatformForAnalytics(),
        'organizationUuid': oauth_account.get('organizationUuid'),
        'accountUuid': oauth_account.get('accountUuid'),
        'userType': os.environ.get('USER_TYPE'),
        'subscriptionType': subscription_type,
        'rateLimitTier': rate_limit_tier,
        'firstTokenTime': first_token_time,
    }
    if is_env_truthy(os.environ.get('GITHUB_ACTIONS')):
        result['githubActionsMetadata'] = {
            'actor': os.environ.get('GITHUB_ACTOR'),
            'actorId': os.environ.get('GITHUB_ACTOR_ID'),
            'repository': os.environ.get('GITHUB_REPOSITORY'),
            'repositoryId': os.environ.get('GITHUB_REPOSITORY_ID'),
            'repositoryOwner': os.environ.get('GITHUB_REPOSITORY_OWNER'),
            'repositoryOwnerId': os.environ.get('GITHUB_REPOSITORY_OWNER_ID'),
        }
    return result


@lru_cache(maxsize=None)
async def getGitEmail() -> str | None:
    result = await exec_file_no_throw('git', ['config', '--get', 'user.email'], cwd=getCwd())
    stdout = (result.get('stdout') or '').strip()
    return stdout if result.get('code') == 0 and stdout else None


async def initUser():
    """Initialize user data asynchronously. Should be called early in startup."""
    global cachedEmail, emailFetchPromise
    if cachedEmail is _EMAIL_NOT_FETCHED and emailFetchPromise is None:
        emailFetchPromise = asyncio.create_task(getEmailAsync())
        cachedEmail = await emailFetchPromise
        emailFetchPromise = None
        getCoreUserData.cache_clear()


def resetUserCache():
    """Reset all user data caches. Call on auth changes (login/logout/account switch)"""
    global cachedEmail, emailFetchPromise
    cachedEmail = _EMAIL_NOT_FETCHED
    emailFetchPromise = None
    getCoreUserData.cache_clear()
    cache_clear = getattr(getGitEmail, 'cache_clear', None)
    if callable(cache_clear):
        cache_clear()


def getUserForGrowthBook():
    """Get user data for GrowthBook (same as core data with analytics metadata)."""
    return getCoreUserData(True)


def getEmail():
    if cachedEmail is not _EMAIL_NOT_FETCHED:
        return cachedEmail if isinstance(cachedEmail, str) else None

    oauth_account = _get_oauth_account_info() or {}
    if oauth_account.get('emailAddress'):
        return oauth_account.get('emailAddress')

    if os.environ.get('USER_TYPE') != 'ant':
        return None

    if os.environ.get('COO_CREATOR'):
        return f"{os.environ['COO_CREATOR']}@anthropic.com"

    return None


async def getEmailAsync():
    oauth_account = _get_oauth_account_info() or {}
    if oauth_account.get('emailAddress'):
        return oauth_account.get('emailAddress')

    if os.environ.get('USER_TYPE') != 'ant':
        return None

    if os.environ.get('COO_CREATOR'):
        return f"{os.environ['COO_CREATOR']}@anthropic.com"

    return await getGitEmail()


init_user = initUser
reset_user_cache = resetUserCache
get_user_for_growth_book = getUserForGrowthBook
get_email = getEmail
get_email_async = getEmailAsync
get_core_user_data = getCoreUserData
get_git_email = getGitEmail

