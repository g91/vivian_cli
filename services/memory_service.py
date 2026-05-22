"""Memory service — wraps Vivian's memory API endpoints."""

from __future__ import annotations

import logging
from typing import Any, Optional

from ..api.client import VivianClient

logger = logging.getLogger(__name__)


class MemoryService:
    """Service for reading/writing Vivian's memory."""

    def __init__(self, client: VivianClient):
        self.client = client

    async def get_core_memories(self, category: Optional[str] = None) -> list[dict]:
        """Get core memories, optionally filtered by category."""
        return await self.client.memory.list_core(category=category)

    async def add_core_memory(
        self, category: str, key: str, value: str, importance: int = 5
    ) -> dict:
        """Add a core memory fact."""
        return await self.client.memory.create_core(
            category=category, key=key, value=value, importance=importance
        )

    async def update_core_memory(self, memory_id: str, **fields) -> dict:
        """Update a core memory."""
        return await self.client.memory.update_core(memory_id, **fields)

    async def delete_core_memory(self, memory_id: str) -> dict:
        """Delete a core memory."""
        return await self.client.memory.delete_core(memory_id)

    async def get_episodic_memories(
        self, user_id: Optional[str] = None, limit: int = 50
    ) -> list[dict]:
        """Get episodic (conversation) memories."""
        return await self.client.memory.list_episodic(user_id=user_id, limit=limit)

    async def add_episodic_memory(
        self,
        content: str,
        user_id: Optional[str] = None,
        importance: int = 4,
        tags: Optional[list[str]] = None,
        summary: str = "",
    ) -> dict:
        """Add an episodic memory."""
        return await self.client.memory.create_episodic(
            content=content,
            user_id=user_id,
            importance=importance,
            tags=tags,
            summary=summary,
        )

    async def delete_episodic_memory(self, memory_id: str) -> dict:
        """Delete an episodic memory."""
        return await self.client.memory.delete_episodic(memory_id)

    async def get_relevant_memories(
        self, query: str, user_id: Optional[str] = None
    ) -> list[dict]:
        """Get memories relevant to a query (combines core + episodic)."""
        core = await self.get_core_memories()
        episodic = await self.get_episodic_memories(user_id=user_id)
        # Simple relevance: return all for now
        return core + episodic
