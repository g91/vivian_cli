"""
    pass of src/utils/undercover
"""
from __future__ import annotations

import os

from .config import get_global_config
from .envUtils import is_env_truthy


def _get_repo_class_cached() -> str | None:
    try:
        from .commitAttribution import getRepoClassCached

        value = getRepoClassCached()
        return value if isinstance(value, str) else None
    except Exception:
        return None


def isUndercover():
    if os.environ.get("USER_TYPE", "") == 'ant':
        if is_env_truthy(os.environ.get("vivian_CODE_UNDERCOVER", "")):
            return True
        # Auto: active unless we've positively confirmed we're in an allowlisted
        # internal repo. 'external', 'none', and null (check not yet run) all
        # resolve to ON. The check is primed in setup.ts; only 'internal' → OFF.
        return _get_repo_class_cached() != 'internal'
    return False


def getUndercoverInstructions():
    if os.environ.get("USER_TYPE", "") == 'ant':
        return """## UNDERCOVER MODE - CRITICAL

You are operating UNDERCOVER in a PUBLIC/OPEN-SOURCE repository. Your commit
messages, PR titles, and PR bodies MUST NOT contain ANY Anthropic-internal
information. Do not blow your cover.

NEVER include in commit messages or PR descriptions:
- Internal model codenames (animal names like Capybara, Tengu, etc.)
- Unreleased model version numbers (e.g., opus-4-7, sonnet-4-8)
- Internal repo or project names (e.g., vivian-cli-internal, anthropics/...)
- Internal tooling, Slack channels, or short links (e.g., go/cc, #vivian-code-...)
- The phrase \"vivian Code\" or any mention that you are an AI
- Any hint of what model or version you are
- Co-Authored-By lines or any other attribution

Write commit messages as a human developer would - describe only what the code
change does.

GOOD:
- \"Fix race condition in file watcher initialization\"
- \"Add support for custom key bindings\"
- \"Refactor parser for better error messages\"

BAD (never write these):
- \"Fix bug found while testing with vivian Capybara\"
- \"1-shotted by vivian-opus-4-6\"
- \"Generated with vivian Code\"
- \"Co-Authored-By: vivian Opus 4.6 <...>\"
"""
    return ''


def shouldShowUndercoverAutoNotice():
    """Check whether to show the one-time explainer dialog for auto-undercover."""
    if os.environ.get("USER_TYPE", "") == 'ant':
        if is_env_truthy(os.environ.get("vivian_CODE_UNDERCOVER", "")):
            return False
        if not isUndercover():
            return False
        return not bool(get_global_config().get("hasSeenUndercoverAutoNotice"))
    return False


is_undercover = isUndercover
get_undercover_instructions = getUndercoverInstructions
should_show_undercover_auto_notice = shouldShowUndercoverAutoNotice

