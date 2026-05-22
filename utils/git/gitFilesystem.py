"""Filesystem-based git state — mirrors src/utils/git/gitFilesystem.ts"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional, Union


# ---------------------------------------------------------------------------
# resolveGitDir
# ---------------------------------------------------------------------------

_resolve_gitdir_cache: dict[str, Optional[str]] = {}


def clear_resolve_gitdir_cache() -> None:
    _resolve_gitdir_cache.clear()


def resolve_git_dir(start_path: Optional[str] = None) -> Optional[str]:
    """Resolve the actual .git directory, handling worktrees/submodules."""
    from .gitFilesystem import _find_git_root
    cwd = str(Path(start_path or os.getcwd()).resolve())
    if cwd in _resolve_gitdir_cache:
        return _resolve_gitdir_cache[cwd]

    root = _find_git_root(cwd)
    if not root:
        _resolve_gitdir_cache[cwd] = None
        return None

    git_path = str(Path(root) / ".git")
    if Path(git_path).is_file():
        content = Path(git_path).read_text(encoding="utf-8").strip()
        if content.startswith("gitdir:"):
            raw_dir = content[len("gitdir:"):].strip()
            resolved = str(Path(root) / raw_dir)
            _resolve_gitdir_cache[cwd] = resolved
            return resolved
    _resolve_gitdir_cache[cwd] = git_path
    return git_path


def _find_git_root(cwd: str) -> Optional[str]:
    """Walk up from cwd looking for a .git directory or file."""
    p = Path(cwd)
    while True:
        candidate = p / ".git"
        if candidate.exists():
            return str(p)
        parent = p.parent
        if parent == p:
            return None
        p = parent


# ---------------------------------------------------------------------------
# isSafeRefName / isValidGitSha
# ---------------------------------------------------------------------------

def is_safe_ref_name(name: str) -> bool:
    """Validate a ref/branch name read from .git/ is safe."""
    if not name or name.startswith("-") or name.startswith("/"):
        return False
    if ".." in name:
        return False
    if any(c in (".", "") for c in name.split("/")):
        return False
    return bool(re.match(r"^[a-zA-Z0-9/._+@-]+$", name))


def is_valid_git_sha(s: str) -> bool:
    """Return True if s is a 40- or 64-character lowercase hex string."""
    return bool(re.match(r"^[0-9a-f]{40}$", s)) or bool(re.match(r"^[0-9a-f]{64}$", s))


# ---------------------------------------------------------------------------
# readGitHead
# ---------------------------------------------------------------------------

async def read_git_head(
    git_dir: str,
) -> Optional[Union[dict, None]]:
    """Parse .git/HEAD and return branch or detached SHA info.

    Returns::

        {'type': 'branch', 'name': str}
        {'type': 'detached', 'sha': str}
        None on error
    """
    try:
        content = (Path(git_dir) / "HEAD").read_text(encoding="utf-8").strip()
    except OSError:
        return None

    if content.startswith("ref:"):
        ref = content[4:].strip()
        if ref.startswith("refs/heads/"):
            name = ref[len("refs/heads/"):]
            if not is_safe_ref_name(name):
                return None
            return {"type": "branch", "name": name}
        if not is_safe_ref_name(ref):
            return None
        sha = await resolve_ref(git_dir, ref)
        return {"type": "detached", "sha": sha or ""}

    if not is_valid_git_sha(content):
        return None
    return {"type": "detached", "sha": content}


# ---------------------------------------------------------------------------
# resolveRef
# ---------------------------------------------------------------------------

async def resolve_ref(git_dir: str, ref: str) -> Optional[str]:
    """Resolve a ref name to a SHA by checking loose files then packed-refs."""
    result = _resolve_ref_in_dir(git_dir, ref)
    if result:
        return result
    common = _get_common_dir(git_dir)
    if common and common != git_dir:
        return _resolve_ref_in_dir(common, ref)
    return None


def _resolve_ref_in_dir(git_dir: str, ref: str, depth: int = 5) -> Optional[str]:
    if depth <= 0:
        return None
    loose = Path(git_dir) / ref
    try:
        content = loose.read_text(encoding="utf-8").strip()
        if content.startswith("ref:"):
            next_ref = content[4:].strip()
            if not is_safe_ref_name(next_ref):
                return None
            return _resolve_ref_in_dir(git_dir, next_ref, depth - 1)
        if is_valid_git_sha(content):
            return content
    except OSError:
        pass
    # packed-refs
    packed = Path(git_dir) / "packed-refs"
    try:
        for line in packed.read_text(encoding="utf-8").split("\n"):
            if line.startswith("#") or line.startswith("^"):
                continue
            parts = line.strip().split(" ", 1)
            if len(parts) == 2 and parts[1] == ref and is_valid_git_sha(parts[0]):
                return parts[0]
    except OSError:
        pass
    return None


def _get_common_dir(git_dir: str) -> Optional[str]:
    """Read the commondir file for worktrees."""
    try:
        raw = (Path(git_dir) / "commondir").read_text(encoding="utf-8").strip()
        if os.path.isabs(raw):
            return raw
        return str(Path(git_dir) / raw)
    except OSError:
        return None


# Public alias used by higher-level code
get_common_dir = _get_common_dir


# ---------------------------------------------------------------------------
# readRawSymref
# ---------------------------------------------------------------------------

def read_raw_symref(
    git_dir: str,
    ref_path: str,
    branch_prefix: str,
) -> Optional[str]:
    """Read a loose symref file and extract the branch name after *branch_prefix*.

    Returns None if the ref doesn't exist, isn't a symref, or doesn't match
    the prefix.  Packed-refs never stores symrefs, so we only check loose files.
    """
    try:
        content = (Path(git_dir) / ref_path).read_text(encoding="utf-8").strip()
        if content.startswith("ref:"):
            target = content[4:].strip()
            if target.startswith(branch_prefix):
                name = target[len(branch_prefix):]
                if not is_safe_ref_name(name):
                    return None
                return name
    except OSError:
        pass
    _path = str(git_dir)
    if not _path or not os.path.exists(_path): return None
    with open(_path, "r", encoding="utf-8") as _f: return _f.read()


# ---------------------------------------------------------------------------
# Cached branch / HEAD / remote URL / default branch
# ---------------------------------------------------------------------------

# Simple in-process cache; no file watchers in the Python port.
_cache: dict[str, object] = {}
_cache_dirty: bool = True


def _invalidate_cache() -> None:
    global _cache_dirty
    _cache_dirty = True
    _cache.clear()


async def _compute_branch() -> str:
    git_dir = resolve_git_dir()
    if not git_dir:
        return "HEAD"
    head = await read_git_head(git_dir)
    if not head:
        return "HEAD"
    return head["name"] if head["type"] == "branch" else "HEAD"


async def _compute_head() -> str:
    git_dir = resolve_git_dir()
    if not git_dir:
        return ""
    head = await read_git_head(git_dir)
    if not head:
        return ""
    if head["type"] == "branch":
        sha = await resolve_ref(git_dir, f"refs/heads/{head['name']}")
        return sha or ""
    return head.get("sha", "")


async def _compute_remote_url() -> Optional[str]:
    from .gitConfigParser import parse_git_config_value
    git_dir = resolve_git_dir()
    if not git_dir:
        return None
    url = parse_git_config_value(git_dir, "remote", "origin", "url")
    if url:
        return url
    common = _get_common_dir(git_dir)
    if common and common != git_dir:
        return parse_git_config_value(common, "remote", "origin", "url")
    return None


async def _compute_default_branch() -> str:
    git_dir = resolve_git_dir()
    if not git_dir:
        return "main"
    common = _get_common_dir(git_dir) or git_dir
    branch_from_symref = read_raw_symref(
        common, "refs/remotes/origin/HEAD", "refs/remotes/origin/"
    )
    if branch_from_symref:
        return branch_from_symref
    for candidate in ("main", "master"):
        sha = await resolve_ref(common, f"refs/remotes/origin/{candidate}")
        if sha:
            return candidate
    return "main"


async def get_cached_branch() -> str:
    """Return the current branch name (cached)."""
    key = "branch"
    if key not in _cache:
        _cache[key] = await _compute_branch()
    return _cache[key]  # type: ignore[return-value]


async def get_cached_head() -> str:
    """Return the current HEAD SHA (cached)."""
    key = "head"
    if key not in _cache:
        _cache[key] = await _compute_head()
    return _cache[key]  # type: ignore[return-value]


async def get_cached_remote_url() -> Optional[str]:
    """Return the remote origin URL (cached)."""
    key = "remoteUrl"
    if key not in _cache:
        _cache[key] = await _compute_remote_url()
    return _cache[key]  # type: ignore[return-value]


async def get_cached_default_branch() -> str:
    """Return the default branch name inferred from origin (cached)."""
    key = "defaultBranch"
    if key not in _cache:
        _cache[key] = await _compute_default_branch()
    return _cache[key]  # type: ignore[return-value]


def reset_git_file_watcher() -> None:
    """Reset the cache. For testing only."""
    _invalidate_cache()


async def get_head_for_dir(cwd: str) -> Optional[str]:
    """Return the HEAD SHA for an arbitrary directory (not using the cache)."""
    git_dir = resolve_git_dir(cwd)
    if not git_dir:
        return None
    head = await read_git_head(git_dir)
    if not head:
        return None
    if head["type"] == "branch":
        return await resolve_ref(git_dir, f"refs/heads/{head['name']}")
    return head.get("sha") or None
