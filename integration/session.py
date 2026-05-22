"""VivianSession — high-level session object used by other Vivian components.

Wraps QueryEngine + MemoryService + BridgeManager into a single object.

Usage:
    session = await create_session(
        user_id="usr-123",
        system_prompt="You are Vivian, a helpful AI.",
        model="qwen3.6",
    )
    reply = await session.send("What is the capital of France?")
    print(reply)
    await session.close()

Or as an async context manager:
    async with await create_session() as session:
        reply = await session.send("Hello!")
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, AsyncIterator, Callable, Optional

logger = logging.getLogger(__name__)


class VivianSession:
    """A single AI conversation session connected to the Vivian backend."""

    def __init__(
        self,
        query_engine,
        bridge_manager=None,
        memory_service=None,
        user_id: Optional[str] = None,
    ):
        self._qe = query_engine
        self._bridge = bridge_manager
        self._memory = memory_service
        self.user_id = user_id
        self._closed = False

    # ── Message sending ───────────────────────────────────────────────────

    async def send(
        self,
        text: str,
        *,
        stream: bool = False,
        on_token: Optional[Callable[[str], None]] = None,
    ) -> str:
        """Send a message and return the full reply text.

        Args:
            text: The user message.
            stream: If True, stream tokens to on_token callback.
            on_token: Called with each streamed token (only when stream=True).
        """
        if self._closed:
            raise RuntimeError("Session is closed")
        try:
            result = await self._qe.submit_message(text)
            if isinstance(result, str):
                return result
            if hasattr(result, "content"):
                return result.content or ""
            return str(result)
        except Exception as e:
            logger.error(f"[session] send failed: {e}")
            raise

    async def stream(self, text: str) -> AsyncIterator[str]:
        """Stream tokens from the AI response."""
        if self._closed:
            raise RuntimeError("Session is closed")
        try:
            async for chunk in self._qe.stream_message(text):
                yield chunk
        except Exception as e:
            logger.error(f"[session] stream failed: {e}")
            raise

    # ── Memory shortcuts ──────────────────────────────────────────────────

    async def remember(self, key: str, value: str, category: str = "general") -> None:
        """Store a fact in Vivian's persistent memory."""
        if self._memory:
            try:
                await self._memory.add_core_memory(
                    category=category, key=key, value=value
                )
            except Exception as e:
                logger.warning(f"[session] remember failed: {e}")

    async def recall(self, category: Optional[str] = None) -> list[dict]:
        """Retrieve facts from Vivian's persistent memory."""
        if self._memory:
            try:
                return await self._memory.get_core_memories(category=category)
            except Exception as e:
                logger.warning(f"[session] recall failed: {e}")
        return []

    # ── Bridge / remote control ───────────────────────────────────────────

    async def enable_remote_control(self, url: str, token: str) -> None:
        """Enable the bridge so this session is reachable from vivian.d0a.net."""
        if self._bridge:
            await self._bridge.connect(url, token)

    async def disable_remote_control(self) -> None:
        if self._bridge:
            await self._bridge.disconnect()

    # ── History ──────────────────────────────────────────────────────────

    def get_messages(self) -> list:
        """Return the full conversation message list."""
        return list(self._qe.messages)

    def clear_history(self) -> None:
        """Clear conversation history (keeps system prompt)."""
        self._qe.messages.clear()

    # ── Lifecycle ────────────────────────────────────────────────────────

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._bridge:
            await self._bridge.disconnect()

    async def __aenter__(self) -> "VivianSession":
        return self

    async def __aexit__(self, *_) -> None:
        await self.close()


async def create_session(
    *,
    user_id: Optional[str] = None,
    system_prompt: Optional[str] = None,
    append_system_prompt: Optional[str] = None,
    model: Optional[str] = None,
    max_turns: int = 25,
    max_budget_usd: Optional[float] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    enable_bridge: bool = False,
    initial_messages: Optional[list] = None,
    cwd: str = ".",
) -> VivianSession:
    """Create and initialize a new VivianSession.

    This is the primary entry point for programmatic use.

    Args:
        user_id: Optional user identifier (for memory scoping).
        system_prompt: Full system prompt override.
        append_system_prompt: Text appended to the default system prompt.
        model: Model name (default from VIVIAN_DEFAULT_MODEL or qwen3.6).
        max_turns: Max agentic turns per query.
        max_budget_usd: Spend limit (None = unlimited).
        api_key: API key override (default from VIVIAN_API_KEY env var).
        base_url: API base URL override.
        enable_bridge: Whether to start the remote control bridge.
        initial_messages: Seed conversation messages.
        cwd: Working directory for file tools.

    Returns:
        A ready-to-use VivianSession.
    """
    from .config import get_config
    from ..api.client import VivianClient
    from ..query_engine import QueryEngine
    from ..services.memory_service import MemoryService
    from ..bridge.manager import BridgeManager
    from ..types import PermissionMode

    cfg = get_config()
    resolved_key = api_key or cfg.api_key
    resolved_url = base_url or cfg.base_api_url
    resolved_model = model or cfg.default_model

    client = VivianClient(
        api_key=resolved_key,
        base_url=resolved_url,
        default_model=resolved_model,
        timeout=cfg.timeout,
    )

    qe = QueryEngine(
        client=client,
        model=resolved_model,
        max_turns=max_turns,
        max_budget_usd=max_budget_usd,
        custom_system_prompt=system_prompt,
        append_system_prompt=append_system_prompt,
        initial_messages=initial_messages or [],
        username=user_id,
        cwd=cwd,
    )

    memory_service = MemoryService(client)
    bridge_manager = BridgeManager() if enable_bridge or cfg.bridge_enabled else None

    session = VivianSession(
        query_engine=qe,
        bridge_manager=bridge_manager,
        memory_service=memory_service,
        user_id=user_id,
    )

    return session
