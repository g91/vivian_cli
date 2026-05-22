"""
Port of src/utils/githubRepoPathMapping.ts
"""
from __future__ import annotations

from typing import Any
import os
import os.path
import asyncio
import glob
import unicodedata

from ..bootstrap.state import getOriginalCwd
from .config import get_global_config, save_global_config
from .debug import logForDebugging
from .detectRepository import detectCurrentRepository, parseGitHubRepository
from .git import findGitRoot, get_remote_url


async def updateGithubRepoPathMapping():
    """Updates the GitHub repository path mapping in global config.
Called at startup (fire-and-forget) to track known local paths for repos.
This is non-blocking and errors are logged silently.

Stores the git root (not cwd) so the mapping always points to the
repository root regardless of which subdirectory the user launched from.
If the path is already tracked, it is promoted to the front of the list
so the most recently used clone appears first."""
    try:
        repo = await detectCurrentRepository()
        if not repo:
            logForDebugging('Not in a GitHub repository, skipping path mapping update')
            return None

        cwd = getOriginalCwd()
        git_root = findGitRoot(cwd)
        base_path = git_root or cwd

        try:
            current_path = unicodedata.normalize('NFC', os.path.realpath(base_path))
        except Exception:
            current_path = base_path

        repo_key = repo.lower()
        config = get_global_config()
        existing_paths = list((config.get('githubRepoPaths') or {}).get(repo_key, []))

        if existing_paths and existing_paths[0] == current_path:
            logForDebugging(f'Path {current_path} already tracked for repo {repo_key}')
            return None

        updated_paths = [current_path, *[path for path in existing_paths if path != current_path]]

        def _update(current):
            mapping = dict(current.get('githubRepoPaths') or {})
            mapping[repo_key] = updated_paths
            return {**current, 'githubRepoPaths': mapping}

        save_global_config(_update)
        logForDebugging(f'Added {current_path} to tracked paths for repo {repo_key}')
    except Exception as error:
        logForDebugging(f'Error updating repo path mapping: {error}')
    return None


def getKnownPathsForRepo(repo):
    """Gets known local paths for a given GitHub repository.
@param repo The repository in "owner/repo" format
@returns Array of known absolute paths, or empty array if none"""
    config = get_global_config()
    repo_key = str(repo).lower()
    return list((config.get('githubRepoPaths') or {}).get(repo_key, []))


async def filterExistingPaths(paths):
    """Filters paths to only those that exist on the filesystem.
@param paths Array of absolute paths to check
@returns Array of paths that exist"""
    if not paths:
        return []
    results = await asyncio.gather(*[asyncio.to_thread(os.path.exists, path) for path in paths])
    return [path for path, exists in zip(paths, results) if exists]


async def validateRepoAtPath(path, expectedRepo):
    """Validates that a path contains the expected GitHub repository.
@param path Absolute path to check
@param expectedRepo Expected repository in "owner/repo" format
@returns true if the path contains the expected repo, false otherwise"""
    try:
        remote_url = await get_remote_url(cwd=path)
        if not remote_url:
            return False
        actual_repo = parseGitHubRepository(remote_url)
        if not actual_repo:
            return False
        return actual_repo.lower() == str(expectedRepo).lower()
    except Exception:
        return False


def removePathFromRepo(repo, pathToRemove):
    """Removes a path from the tracked paths for a given repository.
Used when a path is found to be invalid during selection.
@param repo The repository in "owner/repo" format
@param pathToRemove The path to remove from tracking"""
    config = get_global_config()
    repo_key = str(repo).lower()
    existing_paths = list((config.get('githubRepoPaths') or {}).get(repo_key, []))
    updated_paths = [path for path in existing_paths if path != pathToRemove]
    if len(updated_paths) == len(existing_paths):
        return None

    updated_mapping = dict(config.get('githubRepoPaths') or {})
    if updated_paths:
        updated_mapping[repo_key] = updated_paths
    else:
        updated_mapping.pop(repo_key, None)

    save_global_config(lambda current: {**current, 'githubRepoPaths': updated_mapping})
    logForDebugging(f'Removed {pathToRemove} from tracked paths for repo {repo_key}')
    return None


update_github_repo_path_mapping = updateGithubRepoPathMapping
get_known_paths_for_repo = getKnownPathsForRepo
filter_existing_paths = filterExistingPaths
validate_repo_at_path = validateRepoAtPath
remove_path_from_repo = removePathFromRepo

