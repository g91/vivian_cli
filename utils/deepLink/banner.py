"""Port of src/utils/deepLink/banner.ts."""
from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ..format import format_number


STALE_FETCH_WARN_MS = 7 * 24 * 60 * 60 * 1000
LONG_PREFILL_THRESHOLD = 1000


@dataclass(slots=True)
class DeepLinkBannerInfo:
    cwd: str
    prefillLength: int | None = None
    repo: str | None = None
    lastFetch: datetime | None = None


def _format_relative_time_ago(value: datetime) -> str:
    now = datetime.now(timezone.utc)
    target = value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
    delta = now - target
    if delta < timedelta(minutes=1):
        return "just now"
    if delta < timedelta(hours=1):
        minutes = max(1, int(delta.total_seconds() // 60))
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    if delta < timedelta(days=1):
        hours = max(1, int(delta.total_seconds() // 3600))
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    if delta < timedelta(days=30):
        days = max(1, delta.days)
        return f"{days} day{'s' if days != 1 else ''} ago"
    months = max(1, delta.days // 30)
    return f"{months} month{'s' if months != 1 else ''} ago"


def buildDeepLinkBanner(info: DeepLinkBannerInfo | dict) -> str:
    if isinstance(info, dict):
        info = DeepLinkBannerInfo(**info)
    lines = [f"This session was opened by an external deep link in {tildify(info.cwd)}"]
    if info.repo:
        age = _format_relative_time_ago(info.lastFetch) if info.lastFetch else "never"
        last_fetch = info.lastFetch.astimezone(timezone.utc) if info.lastFetch and info.lastFetch.tzinfo else info.lastFetch.replace(tzinfo=timezone.utc) if info.lastFetch else None
        stale = last_fetch is None or (datetime.now(timezone.utc) - last_fetch).total_seconds() * 1000 > STALE_FETCH_WARN_MS
        lines.append(
            f"Resolved {info.repo} from local clones · last fetched {age}{' — vivian.md may be stale' if stale else ''}"
        )
    if info.prefillLength:
        if info.prefillLength > LONG_PREFILL_THRESHOLD:
            lines.append(
                f"The prompt below ({format_number(info.prefillLength)} chars) was supplied by the link — scroll to review the entire prompt before pressing Enter."
            )
        else:
            lines.append("The prompt below was supplied by the link — review carefully before pressing Enter.")
    return "\n".join(lines)


async def _run_git(cwd: str, *args: str) -> str | None:
    try:
        proc = await asyncio.create_subprocess_exec(
            "git",
            *args,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode == 0:
            return stdout.decode(errors="replace").strip() or None
    except Exception:
        return None
    return None


async def _get_git_dir(cwd: str) -> str | None:
    result = await _run_git(cwd, "rev-parse", "--git-dir")
    if not result:
        return None
    return result if os.path.isabs(result) else os.path.normpath(os.path.join(cwd, result))


async def _get_common_dir(git_dir: str) -> str | None:
    cwd = git_dir if os.path.isdir(git_dir) else os.path.dirname(git_dir)
    result = await _run_git(cwd, "rev-parse", "--git-common-dir")
    if not result:
        return None
    return result if os.path.isabs(result) else os.path.normpath(os.path.join(cwd, result))


async def readLastFetchTime(cwd: str):
    git_dir = await _get_git_dir(cwd)
    if not git_dir:
        return None
    common_dir = await _get_common_dir(git_dir)
    local, common = await asyncio.gather(
        mtimeOrUndefined(os.path.join(git_dir, "FETCH_HEAD")),
        mtimeOrUndefined(os.path.join(common_dir, "FETCH_HEAD")) if common_dir else asyncio.sleep(0, result=None),
    )
    if local and common:
        return local if local > common else common
    return local or common


async def mtimeOrUndefined(p: str):
    try:
        stat = await asyncio.to_thread(os.stat, p)
    except Exception:
        return None
    return datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)


def tildify(p: str) -> str:
    home = str(Path.home())
    if p == home:
        return "~"
    if p.startswith(home + os.sep):
        return "~" + p[len(home) :]
    return p


build_deep_link_banner = buildDeepLinkBanner
read_last_fetch_time = readLastFetchTime
mtime_or_undefined = mtimeOrUndefined

