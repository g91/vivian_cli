"""Lightweight git helpers exposed from the live utils.git package."""
from __future__ import annotations

import os
import subprocess
from typing import Optional


def _default_cwd(cwd: Optional[str] = None) -> str:
	if cwd:
		return cwd
	try:
		from ..cwd import get_cwd

		return get_cwd()
	except Exception:
		return os.getcwd()


def _run_git(args: list[str], cwd: Optional[str] = None) -> Optional[str]:
	try:
		result = subprocess.run(
			["git", *args],
			capture_output=True,
			text=True,
			cwd=_default_cwd(cwd),
		)
		if result.returncode == 0:
			return result.stdout.strip()
	except Exception:
		pass
	return None


async def get_branch(cwd: Optional[str] = None) -> str:
	return _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd) or ""


async def get_default_branch(cwd: Optional[str] = None) -> str:
	remote_head = _run_git(["symbolic-ref", "refs/remotes/origin/HEAD"], cwd=cwd)
	if remote_head and "/" in remote_head:
		return remote_head.rsplit("/", 1)[-1]
	return ""


async def get_remote_url(cwd: Optional[str] = None) -> Optional[str]:
	return _run_git(["remote", "get-url", "origin"], cwd=cwd)


async def getIsClean(ignoreUntracked: bool = False, cwd: Optional[str] = None) -> bool:
	args = ["status", "--porcelain"]
	if ignoreUntracked:
		args.append("--untracked-files=no")
	output = _run_git(args, cwd=cwd)
	return output == ""


def findGitRoot(startPath: str) -> Optional[str]:
	return _run_git(["rev-parse", "--show-toplevel"], cwd=startPath)


def findCanonicalGitRoot(startPath: str) -> Optional[str]:
	return findGitRoot(startPath)


getBranch = get_branch
getDefaultBranch = get_default_branch
getRemoteUrl = get_remote_url
