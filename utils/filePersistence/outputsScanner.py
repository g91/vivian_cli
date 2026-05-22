"""Port of src/utils/filePersistence/outputsScanner.ts"""
from __future__ import annotations
import asyncio
import os
import os.path
from typing import List, Optional

from vivian_cli.utils.debug import logForDebugging


def logDebug(message: str) -> None:
    """Shared debug logger for file persistence modules."""
    logForDebugging(f"[file-persistence] {message}")


def getEnvironmentKind() -> Optional[str]:
    """Get the environment kind from vivian_CODE_ENVIRONMENT_KIND.
    Returns None if not set or not a recognized value.
    """
    kind = os.environ.get("vivian_CODE_ENVIRONMENT_KIND")
    if kind in ("byoc", "anthropic_cloud"):
        return kind
    return None


async def findModifiedFiles(turnStartTime: float, outputsDir: str) -> List[str]:
    """Find files that have been modified since the turn started.
    Returns paths of files with mtime >= turnStartTime.

    Uses recursive directory listing and parallelized stat calls for efficiency.
    """
    loop = asyncio.get_event_loop()
    try:
        all_entries = await loop.run_in_executor(None, lambda: list(_walk_files(outputsDir)))
    except OSError:
        return []

    if not all_entries:
        logDebug("No files found in outputs directory")
        return []

    async def stat_file(file_path: str):
        try:
            stat_result = await loop.run_in_executor(None, lambda: os.lstat(file_path))
            import stat as stat_mod
            if stat_mod.S_ISLNK(stat_result.st_mode):
                return None
            return {"filePath": file_path, "mtimeMs": stat_result.st_mtime * 1000}
        except OSError:
            return None

    stat_results = await asyncio.gather(*[stat_file(p) for p in all_entries])

    modified_files: List[str] = []
    for result in stat_results:
        if result and result["mtimeMs"] >= turnStartTime:
            modified_files.append(result["filePath"])

    logDebug(
        f"Found {len(modified_files)} modified files since turn start "
        f"(scanned {len(all_entries)} total)"
    )

    return modified_files


def _walk_files(directory: str):
    """Walk directory recursively, yield regular file paths, skip symlinks."""
    for dirpath, dirnames, filenames in os.walk(directory, followlinks=False):
        for fname in filenames:
            full_path = os.path.join(dirpath, fname)
            if os.path.islink(full_path):
                continue
            yield full_path
