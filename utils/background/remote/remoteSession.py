"""Port of src/utils/background/remote/remoteSession.ts"""
from __future__ import annotations
import asyncio
import os
from typing import Any, Dict, List, Optional

# Type aliases
BackgroundRemoteSession = Dict[str, Any]
"""
{
    'id': str,
    'command': str,
    'startTime': int,
    'status': 'starting' | 'running' | 'completed' | 'failed' | 'killed',
    'todoList': Any,  # TodoList
    'title': str,
    'type': 'remote_session',
    'log': list,  # SDKMessage[]
}
"""

BackgroundRemoteSessionPrecondition = Dict[str, str]
"""
{ 'type': 'not_logged_in' } |
{ 'type': 'no_remote_environment' } |
{ 'type': 'not_in_git_repo' } |
{ 'type': 'no_git_remote' } |
{ 'type': 'github_app_not_installed' } |
{ 'type': 'policy_blocked' }
"""


async def checkBackgroundRemoteSessionEligibility(
    skipBundle: bool = False,
) -> List[Dict[str, str]]:
    """Checks eligibility for creating a background remote session.
    Returns an array of failed preconditions (empty array means all checks passed).
    """
    from vivian_cli.utils.background.remote.preconditions import (
        checkNeedsvivianAiLogin,
        checkHasRemoteEnvironment,
        checkIsInGitRepo,
        checkGithubAppInstalled,
    )

    errors: List[Dict[str, str]] = []

    # Check policy first - if blocked, no need to check other preconditions
    try:
        from vivian_cli.utils.services.policyLimits import isPolicyAllowed
        if not isPolicyAllowed('allow_remote_sessions'):
            errors.append({'type': 'policy_blocked'})
            return errors
    except Exception:
        pass

    try:
        from vivian_cli.utils.detectRepository import detectCurrentRepositoryWithHost
        needs_login, has_remote_env, repository = await asyncio.gather(
            checkNeedsvivianAiLogin(),
            checkHasRemoteEnvironment(),
            detectCurrentRepositoryWithHost(),
        )
    except Exception:
        needs_login, has_remote_env, repository = False, False, None

    if needs_login:
        errors.append({'type': 'not_logged_in'})

    if not has_remote_env:
        errors.append({'type': 'no_remote_environment'})

    # When bundle seeding is on, in-git-repo is enough — CCR can seed from
    # a local bundle. No GitHub remote or app needed. Same gate as
    # teleport.tsx bundleSeedGateOn.
    bundle_seed_gate_on = False
    if not skipBundle:
        try:
            from vivian_cli.utils.envUtils import isEnvTruthy
            from vivian_cli.utils.services.analytics.growthbook import checkGate_CACHED_OR_BLOCKING
            bundle_seed_gate_on = (
                isEnvTruthy(os.environ.get('CCR_FORCE_BUNDLE'))
                or isEnvTruthy(os.environ.get('CCR_ENABLE_BUNDLE'))
                or await checkGate_CACHED_OR_BLOCKING('tengu_ccr_bundle_seed_enabled')
            )
        except Exception:
            bundle_seed_gate_on = (
                os.environ.get('CCR_FORCE_BUNDLE', '').lower() in ('1', 'true', 'yes')
                or os.environ.get('CCR_ENABLE_BUNDLE', '').lower() in ('1', 'true', 'yes')
            )

    if not checkIsInGitRepo():
        errors.append({'type': 'not_in_git_repo'})
    elif bundle_seed_gate_on:
        # has .git/, bundle will work — skip remote+app checks
        pass
    elif repository is None:
        errors.append({'type': 'no_git_remote'})
    elif isinstance(repository, dict) and repository.get('host') == 'github.com':
        has_github_app = await checkGithubAppInstalled(
            repository.get('owner', ''),
            repository.get('name', ''),
        )
        if not has_github_app:
            errors.append({'type': 'github_app_not_installed'})

    return errors
