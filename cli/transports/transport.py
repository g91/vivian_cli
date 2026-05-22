"""Abstract Transport interface — mirrors the Transport interface in src/cli/transports/."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Awaitable, Callable, Optional


class Transport(ABC):
    """Common interface for all stream transports (SSE, WebSocket, Hybrid)."""

    def set_on_data(self, callback: Callable[[str], None]) -> None:
        self._on_data = callback

    def set_on_close(self, callback: Callable[[Optional[int]], None]) -> None:
        self._on_close = callback

    @abstractmethod
    async def connect(self) -> None:
        """Establish the connection and start receiving data."""

    @abstractmethod
    async def send(self, data: str) -> None:
        """Send data to the remote end."""

    @abstractmethod
    async def close(self) -> None:
        """Close the connection."""

    def _emit_data(self, data: str) -> None:
        if hasattr(self, "_on_data") and self._on_data:
            self._on_data(data)

    def _emit_close(self, code: Optional[int] = None) -> None:
        if hasattr(self, "_on_close") and self._on_close:
            self._on_close(code)
