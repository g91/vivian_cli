"""Context package — mirrors src/context/ and top-level src/context.ts."""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import Optional

from ..bootstrap.state import (
    getAdditionalDirectoriesForvivianMd,
    setCachedvivianMdContent,
)
from ..constants.common import getLocalISODate
from ..utils.vivianmd import find_vivian_md
from ..utils.cwd import get_cwd
from ..utils.diagLogs import logForDiagnosticsNoPII
from ..utils.envUtils import is_bare_mode, is_env_defined_falsy, is_env_truthy
from .fpsMetrics import FpsMetricsProvider, GetFpsMetricsContext, useFpsMetrics
from .mailbox import MailboxContext, useMailbox
from .notifications import NotificationsContext, useNotifications
from .stats import StatsContext, useStats
from .voice import VoiceContext, useVoice


MAX_STATUS_CHARS = 2000
_system_prompt_injection: Optional[str] = None
_git_status_cache: Optional[str] = None
_git_status_cache_set = False
_system_context_cache: Optional[dict[str, str]] = None
_user_context_cache: Optional[dict[str, str]] = None


def _clear_context_caches() -> None:
    global _git_status_cache, _git_status_cache_set, _system_context_cache, _user_context_cache
    _git_status_cache = None
    _git_status_cache_set = False
    _system_context_cache = None
    _user_context_cache = None


def getSystemPromptInjection() -> Optional[str]:
    return _system_prompt_injection


def setSystemPromptInjection(value: Optional[str]) -> None:
    global _system_prompt_injection
    _system_prompt_injection = value
    _clear_context_caches()


def _run_git(args: list[str], cwd: str) -> str:
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        cwd=cwd,
        timeout=10,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git command failed")
    return result.stdout.strip()


def _should_include_git_instructions() -> bool:
    env_val = os.environ.get("vivian_CODE_DISABLE_GIT_INSTRUCTIONS")
    if is_env_truthy(env_val):
        return False
    if is_env_defined_falsy(env_val):
        return True
    return True


def _collect_vivian_md_paths(cwd: str) -> list[Path]:
    paths: list[Path] = []
    primary = find_vivian_md(cwd)
    if primary:
        paths.append(Path(primary))
    for directory in getAdditionalDirectoriesForvivianMd():
        found = find_vivian_md(directory)
        if found:
            path = Path(found)
            if path not in paths:
                paths.append(path)
    return paths


def _read_vivian_md_bundle(cwd: str) -> Optional[str]:
    chunks: list[str] = []
    paths = _collect_vivian_md_paths(cwd)
    for path in paths:
        try:
            content = path.read_text(encoding="utf-8").strip()
        except Exception:
            continue
        if not content:
            continue
        chunks.append(content if len(paths) == 1 else f"# {path}\n\n{content}")
    return "\n\n".join(chunks) or None


def getGitStatus() -> Optional[str]:
    global _git_status_cache, _git_status_cache_set
    if _git_status_cache_set:
        return _git_status_cache
    if os.environ.get("NODE_ENV") == "test":
        _git_status_cache_set = True
        _git_status_cache = None
        return None

    start_time = time.time() * 1000
    cwd = get_cwd()
    logForDiagnosticsNoPII("info", "git_status_started")

    try:
        is_git_start = time.time() * 1000
        inside_repo = _run_git(["rev-parse", "--is-inside-work-tree"], cwd) == "true"
        logForDiagnosticsNoPII(
            "info",
            "git_is_git_check_completed",
            {"duration_ms": int(time.time() * 1000 - is_git_start), "is_git": inside_repo},
        )
        if not inside_repo:
            logForDiagnosticsNoPII(
                "info",
                "git_status_skipped_not_git",
                {"duration_ms": int(time.time() * 1000 - start_time)},
            )
            _git_status_cache_set = True
            _git_status_cache = None
            return None

        git_cmds_start = time.time() * 1000
        branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd)
        try:
            remote_head = _run_git(["symbolic-ref", "refs/remotes/origin/HEAD"], cwd)
            main_branch = remote_head.rsplit("/", 1)[-1] if "/" in remote_head else ""
        except Exception:
            main_branch = ""
        status = _run_git(["--no-optional-locks", "status", "--short"], cwd)
        log_output = _run_git(["--no-optional-locks", "log", "--oneline", "-n", "5"], cwd)
        try:
            user_name = _run_git(["config", "user.name"], cwd)
        except Exception:
            user_name = ""
        logForDiagnosticsNoPII(
            "info",
            "git_commands_completed",
            {"duration_ms": int(time.time() * 1000 - git_cmds_start), "status_length": len(status)},
        )

        truncated_status = (
            status[:MAX_STATUS_CHARS]
            + '\n... (truncated because it exceeds 2k characters. If you need more information, run "git status" using BashTool)'
            if len(status) > MAX_STATUS_CHARS
            else status
        )
        logForDiagnosticsNoPII(
            "info",
            "git_status_completed",
            {
                "duration_ms": int(time.time() * 1000 - start_time),
                "truncated": len(status) > MAX_STATUS_CHARS,
            },
        )
        sections = [
            "This is the git status at the start of the conversation. Note that this status is a snapshot in time, and will not update during the conversation.",
            f"Current branch: {branch}",
            f"Main branch (you will usually use this for PRs): {main_branch}",
        ]
        if user_name:
            sections.append(f"Git user: {user_name}")
        sections.append(f"Status:\n{truncated_status or '(clean)'}")
        sections.append(f"Recent commits:\n{log_output}")
        _git_status_cache = "\n\n".join(sections)
        _git_status_cache_set = True
        return _git_status_cache
    except Exception:
        logForDiagnosticsNoPII(
            "error",
            "git_status_failed",
            {"duration_ms": int(time.time() * 1000 - start_time)},
        )
        _git_status_cache = None
        _git_status_cache_set = True
        return None


async def getSystemContext() -> dict[str, str]:
    global _system_context_cache
    if _system_context_cache is not None:
        return dict(_system_context_cache)

    start_time = time.time() * 1000
    logForDiagnosticsNoPII("info", "system_context_started")
    git_status = None
    if not is_env_truthy(os.environ.get("vivian_CODE_REMOTE")) and _should_include_git_instructions():
        git_status = getGitStatus()
    injection = getSystemPromptInjection()
    logForDiagnosticsNoPII(
        "info",
        "system_context_completed",
        {
            "duration_ms": int(time.time() * 1000 - start_time),
            "has_git_status": git_status is not None,
            "has_injection": injection is not None,
        },
    )
    result: dict[str, str] = {}
    if git_status:
        result["gitStatus"] = git_status
    if injection:
        result["cacheBreaker"] = f"[CACHE_BREAKER: {injection}]"
    _system_context_cache = dict(result)
    return result


async def getUserContext() -> dict[str, str]:
    global _user_context_cache
    if _user_context_cache is not None:
        return dict(_user_context_cache)

    start_time = time.time() * 1000
    logForDiagnosticsNoPII("info", "user_context_started")
    should_disable_vivian_md = is_env_truthy(os.environ.get("vivian_CODE_DISABLE_vivian_MDS")) or (
        is_bare_mode() and len(getAdditionalDirectoriesForvivianMd()) == 0
    )
    vivian_md = None if should_disable_vivian_md else _read_vivian_md_bundle(get_cwd())
    setCachedvivianMdContent(vivian_md)
    logForDiagnosticsNoPII(
        "info",
        "user_context_completed",
        {
            "duration_ms": int(time.time() * 1000 - start_time),
            "vivianmd_length": len(vivian_md or ""),
            "vivianmd_disabled": bool(should_disable_vivian_md),
        },
    )
    result = {"currentDate": f"Today's date is {getLocalISODate()}."}
    if vivian_md:
        result["vivianMd"] = vivian_md
    _user_context_cache = dict(result)
    return result


get_system_prompt_injection = getSystemPromptInjection
set_system_prompt_injection = setSystemPromptInjection
get_git_status = getGitStatus
get_system_context = getSystemContext
get_user_context = getUserContext


__all__ = [
    "MailboxContext",
    "NotificationsContext",
    "StatsContext",
    "VoiceContext",
    "getGitStatus",
    "getSystemContext",
    "getSystemPromptInjection",
    "getUserContext",
    "get_git_status",
    "get_system_context",
    "get_system_prompt_injection",
    "get_user_context",
    "setSystemPromptInjection",
    "set_system_prompt_injection",
    "useMailbox",
    "useNotifications",
    "useStats",
    "useVoice",
]
