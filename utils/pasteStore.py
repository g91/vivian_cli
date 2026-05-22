"""
Port of src/utils/pasteStore.ts
"""
from __future__ import annotations

import os
import asyncio
import hashlib
from pathlib import Path

from .debug import logForDebugging
from .envUtils import get_vivian_config_home_dir
from .errors import is_enoent


PASTE_STORE_DIR = "paste-cache"


def getPasteStoreDir():
    """Get the paste store directory (persistent across sessions)."""
    return str(Path(get_vivian_config_home_dir()) / PASTE_STORE_DIR)


def hashPastedText(content):
    """Generate a hash for paste content to use as filename.
Exported so callers can get the hash synchronously before async storage."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def getPastePath(hash):
    """Get the file path for a paste by its content hash."""
    return str(Path(getPasteStoreDir()) / f"{hash}.txt")


async def storePastedText(hash, content):
    """Store pasted text content to disk.
The hash should be pre-computed with hashPastedText() so the caller
can use it immediately without waiting for the async disk write."""
    try:
        directory = getPasteStoreDir()
        await asyncio.to_thread(os.makedirs, directory, 0o755, True)
        paste_path = getPastePath(hash)

        def _write() -> None:
            with open(paste_path, "w", encoding="utf-8") as handle:
                handle.write(content)
            os.chmod(paste_path, 0o600)

        await asyncio.to_thread(_write)
        logForDebugging(f"Stored paste {hash} to {paste_path}")
    except Exception as error:
        logForDebugging(f"Failed to store paste: {error}")


async def retrievePastedText(hash):
    """Retrieve pasted text content by its hash.
Returns null if not found or on error."""
    try:
        paste_path = getPastePath(hash)
        return await asyncio.to_thread(Path(paste_path).read_text, encoding="utf-8")
    except Exception as error:
        if not is_enoent(error):
            logForDebugging(f"Failed to retrieve paste {hash}: {error}")
        return None


async def cleanupOldPastes(cutoffDate):
    """Clean up old paste files that are no longer referenced.
This is a simple time-based cleanup - removes files older than cutoffDate."""
    paste_dir = getPasteStoreDir()
    try:
        files = await asyncio.to_thread(os.listdir, paste_dir)
    except Exception:
        return

    cutoff_time = cutoffDate.timestamp() if hasattr(cutoffDate, "timestamp") else float(cutoffDate)
    for filename in files:
        if not filename.endswith(".txt"):
            continue
        file_path = os.path.join(paste_dir, filename)
        try:
            stat_result = await asyncio.to_thread(os.stat, file_path)
            if stat_result.st_mtime < cutoff_time:
                await asyncio.to_thread(os.unlink, file_path)
                logForDebugging(f"Cleaned up old paste: {file_path}")
        except Exception:
            continue


get_paste_store_dir = getPasteStoreDir
hash_pasted_text = hashPastedText
get_paste_path = getPastePath
store_pasted_text = storePastedText
retrieve_pasted_text = retrievePastedText
cleanup_old_pastes = cleanupOldPastes

