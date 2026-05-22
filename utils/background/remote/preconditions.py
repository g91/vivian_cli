"""Port of src/utils/background/remote/preconditions.ts"""
from __future__ import annotations
import asyncio
import json
import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)

RepoAccessMethod = str  # 'github-app' | 'token-sync' | 'none'


async def checkNeedsvivianAiLogin() -> bool:
    """Checks if user needs to log in with api-vivian.d0a.net.
    Extracted from getTeleportErrors() in TeleportError.tsx.
    Returns True if login is required, False otherwise.
    """
    try:
        from vivian_cli.utils.auth import isvivianAISubscriber, checkAndRefreshOAuthTokenIfNeeded
        if not isvivianAISubscriber():
            return False
        return await checkAndRefreshOAuthTokenIfNeeded()
    except Exception:
        return False


async def checkIsGitClean() -> bool:
    """Checks if git working directory is clean (no uncommitted changes).
    Ignores untracked files since they won't be lost during branch switching.
    Returns True if git is clean, False otherwise.
    """
    try:
        from vivian_cli.utils.git import getIsClean
        return await getIsClean(ignoreUntracked=True)
    except Exception:
        return False


async def checkHasRemoteEnvironment() -> bool:
    """Checks if user has access to at least one remote environment.
    Returns True if user has remote environments, False otherwise.
    """
    try:
        from vivian_cli.utils.teleport.environments import fetchEnvironments
        from vivian_cli.utils.debug import logForDebugging
        from vivian_cli.utils.errors import errorMessage
        environments = await fetchEnvironments()
        return len(environments) > 0
    except Exception as error:
        try:
            from vivian_cli.utils.debug import logForDebugging
            from vivian_cli.utils.errors import errorMessage
            logForDebugging(f"checkHasRemoteEnvironment failed: {errorMessage(error)}")
        except Exception:
            logger.debug(f"checkHasRemoteEnvironment failed: {error}")
        return False


def checkIsInGitRepo() -> bool:
    """Checks if current directory is inside a git repository (has .git/).
    Distinct from checkHasGitRemote — a local-only repo passes this but not that.
    """
    try:
        from vivian_cli.utils.git import findGitRoot
        from vivian_cli.utils.cwd import getCwd
        return findGitRoot(getCwd()) is not None
    except Exception:
        return False


async def checkHasGitRemote() -> bool:
    """Checks if current repository has a GitHub remote configured.
    Returns False for local-only repos (git init with no origin).
    """
    try:
        from vivian_cli.utils.detectRepository import detectCurrentRepository
        repository = await detectCurrentRepository()
        return repository is not None
    except Exception:
        return False


async def checkGithubAppInstalled(owner: str, repo: str, signal=None) -> bool:
    """Checks if GitHub app is installed on a specific repository.
    Returns True if GitHub app is installed, False otherwise.
    """
    try:
        from vivian_cli.utils.debug import logForDebugging
        from vivian_cli.utils.errors import errorMessage
        from vivian_cli.utils.auth import getvivianAIOAuthTokens
        from vivian_cli.utils.teleport.api import getOAuthHeaders

        tokens = getvivianAIOAuthTokens()
        access_token = tokens.get('accessToken') if tokens else None
        if not access_token:
            logForDebugging(
                'checkGithubAppInstalled: No access token found, assuming app not installed'
            )
            return False

        from vivian_cli.utils.services.oauth.client import getOrganizationUUID
        org_uuid = await getOrganizationUUID()
        if not org_uuid:
            logForDebugging(
                'checkGithubAppInstalled: No org UUID found, assuming app not installed'
            )
            return False

        from vivian_cli.constants.oauth import getOauthConfig
        base_url = getOauthConfig()['BASE_API_URL']
        url = f"{base_url}/api/oauth/organizations/{org_uuid}/code/repos/{owner}/{repo}"
        headers = {**getOAuthHeaders(access_token), 'x-organization-uuid': org_uuid}

        logForDebugging(f"Checking GitHub app installation for {owner}/{repo}")

        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(
            None, lambda: requests.get(url, headers=headers, timeout=15.0)
        )

        if resp.status_code == 200:
            data = resp.json()
            status = data.get('status')
            if status:
                installed = status.get('app_installed', False)
                logForDebugging(
                    f"GitHub app {'is' if installed else 'is not'} installed on {owner}/{repo}"
                )
                return installed
            logForDebugging(f"GitHub app is not installed on {owner}/{repo} (status is null)")
            return False

        logForDebugging(
            f"checkGithubAppInstalled: Unexpected response status {resp.status_code}"
        )
        return False

    except Exception as error:
        try:
            from vivian_cli.utils.debug import logForDebugging
            from vivian_cli.utils.errors import errorMessage
            if hasattr(error, 'response') and error.response is not None:
                status = error.response.status_code
                if 400 <= status < 500:
                    logForDebugging(
                        f"checkGithubAppInstalled: Got {status} error, app likely not installed on {owner}/{repo}"
                    )
                    return False
            logForDebugging(f"checkGithubAppInstalled error: {errorMessage(error)}")
        except Exception:
            logger.debug(f"checkGithubAppInstalled error: {error}")
        return False


async def checkGithubTokenSynced() -> bool:
    """Checks if the user has synced their GitHub credentials via /web-setup.
    Returns True if GitHub token is synced, False otherwise.
    """
    try:
        from vivian_cli.utils.debug import logForDebugging
        from vivian_cli.utils.errors import errorMessage
        from vivian_cli.utils.auth import getvivianAIOAuthTokens
        from vivian_cli.utils.teleport.api import getOAuthHeaders

        tokens = getvivianAIOAuthTokens()
        access_token = tokens.get('accessToken') if tokens else None
        if not access_token:
            logForDebugging('checkGithubTokenSynced: No access token found')
            return False

        from vivian_cli.utils.services.oauth.client import getOrganizationUUID
        org_uuid = await getOrganizationUUID()
        if not org_uuid:
            logForDebugging('checkGithubTokenSynced: No org UUID found')
            return False

        from vivian_cli.constants.oauth import getOauthConfig
        base_url = getOauthConfig()['BASE_API_URL']
        url = f"{base_url}/api/oauth/organizations/{org_uuid}/sync/github/auth"
        headers = {**getOAuthHeaders(access_token), 'x-organization-uuid': org_uuid}

        logForDebugging('Checking if GitHub token is synced via web-setup')

        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(
            None, lambda: requests.get(url, headers=headers, timeout=15.0)
        )

        synced = resp.status_code == 200 and resp.json().get('is_authenticated') is True
        logForDebugging(
            f"GitHub token synced: {synced} (status={resp.status_code}, data={json.dumps(resp.json())})"
        )
        return synced

    except Exception as error:
        try:
            from vivian_cli.utils.debug import logForDebugging
            from vivian_cli.utils.errors import errorMessage
            if hasattr(error, 'response') and error.response is not None:
                status = error.response.status_code
                if 400 <= status < 500:
                    logForDebugging(f"checkGithubTokenSynced: Got {status}, token not synced")
                    return False
            logForDebugging(f"checkGithubTokenSynced error: {errorMessage(error)}")
        except Exception:
            logger.debug(f"checkGithubTokenSynced error: {error}")
        return False


async def checkRepoForRemoteAccess(owner: str, repo: str) -> dict:
    """Tiered check for whether a GitHub repo is accessible for remote operations.
    1. GitHub App installed on the repo
    2. GitHub token synced via /web-setup
    3. Neither — caller should prompt user to set up access
    """
    if await checkGithubAppInstalled(owner, repo):
        return {'hasAccess': True, 'method': 'github-app'}

    try:
        from vivian_cli.utils.services.analytics.growthbook import getFeatureValue_CACHED_MAY_BE_STALE
        if (
            getFeatureValue_CACHED_MAY_BE_STALE('tengu_cobalt_lantern', False)
            and await checkGithubTokenSynced()
        ):
            return {'hasAccess': True, 'method': 'token-sync'}
    except Exception:
        pass

    return {'hasAccess': False, 'method': 'none'}
