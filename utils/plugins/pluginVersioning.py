"""
Port of src/utils/plugins/pluginVersioning.ts

Plugin Version Calculation Module.
"""
from __future__ import annotations

import hashlib
from typing import Any, Dict, Optional


async def calculatePluginVersion(
    plugin_id: str,
    source: Any,
    manifest: Optional[Dict[str, Any]] = None,
    install_path: Optional[str] = None,
    provided_version: Optional[str] = None,
    git_commit_sha: Optional[str] = None,
) -> str:
    """Calculate the version for a plugin based on its source."""
    # 1. Use explicit version from plugin.json if available
    if manifest and manifest.get("version"):
        return manifest["version"]

    # 2. Use provided version (typically from marketplace entry)
    if provided_version:
        return provided_version

    # 3. Use pre-resolved git SHA if caller captured it
    if git_commit_sha:
        short_sha = git_commit_sha[:12]
        if isinstance(source, dict) and source.get("source") == "git-subdir":
            norm_path = source.get("path", "").replace("\\", "/").replace("./", "", 1).rstrip("/")
            path_hash = hashlib.sha256(norm_path.encode()).hexdigest()[:8]
            return f"{short_sha}-{path_hash}"
        return short_sha

    # 4. Try to get git SHA from install path
    if install_path:
        sha = await getGitCommitSha(install_path)
        if sha:
            return sha[:12]

    return "unknown"


async def getGitCommitSha(dir_path: str) -> Optional[str]:
    """Get the git commit SHA for a directory."""
    try:
        from ..git.gitFilesystem import getHeadForDir
        return await getHeadForDir(dir_path)
    except Exception:
        return None


def getVersionFromPath(install_path: str) -> Optional[str]:
    """Extract version from a versioned cache path."""
    parts = [p for p in install_path.split("/") if p]
    for i, part in enumerate(parts):
        if part == "cache" and i > 0 and parts[i - 1] == "plugins":
            after = parts[i + 1:]
            if len(after) >= 3:
                return after[2]
    return None


def isVersionedPath(path: str) -> bool:
    """Check if a path is a versioned plugin path."""
    return getVersionFromPath(path) is not None

