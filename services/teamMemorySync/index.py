"""Team memory sync service — mirrors src/services/teamMemorySync/index.ts."""
from __future__ import annotations

import hashlib
from typing import Optional


def createSyncState() -> dict:
    """Create a new sync state object.

    Mirrors createSyncState() from index.ts.
    """
    return {"lastSync": None, "pending": [], "active": False}


def hashContent(content: str) -> str:
    """Hash content using SHA-256.

    Mirrors hashContent() from index.ts.
    """
    return hashlib.sha256(content.encode()).hexdigest()


def batchDeltaByBytes(items: list, max_bytes: int) -> list[list]:
    """Batch items into chunks by total byte size.

    Mirrors batchDeltaByBytes() from index.ts.
    """
    batches = []
    current_batch = []
    current_size = 0
    for item in items:
        item_size = len(str(item).encode())
        if current_batch and current_size + item_size > max_bytes:
            batches.append(current_batch)
            current_batch = []
            current_size = 0
        current_batch.append(item)
        current_size += item_size
    if current_batch:
        batches.append(current_batch)
    return batches


def isTeamMemorySyncAvailable() -> bool:
    """Check if team memory sync is available.

    Mirrors isTeamMemorySyncAvailable() from index.ts.
    """
    return False


create_sync_state = createSyncState
hash_content = hashContent
batch_delta_by_bytes = batchDeltaByBytes
is_team_memory_sync_available = isTeamMemorySyncAvailable
