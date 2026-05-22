"""Bridge manager compatibility layer.

Preserves the lightweight in-process BridgeManager API used by tests and
integration code, while routing the standalone `vivian-bridge` console entry
point through the real bridge daemon implementation.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from typing import Any, Optional, Callable

from ..types import BridgeConfig
from .bridgeMain import bridgeMain

logger = logging.getLogger(__name__)


class BridgeManager:
    """Manages bridge connections to remote Vivian sessions."""

    def __init__(self, config: Optional[BridgeConfig] = None):
        self.config = config or BridgeConfig()
        self._connected = False
        self._poll_task: Optional[asyncio.Task] = None
        self._on_message: Optional[Callable[[dict], None]] = None

    @property
    def is_connected(self) -> bool:
        return self._connected

    def set_on_message(self, callback: Callable[[dict], None]):
        self._on_message = callback

    async def connect(self, url: str, auth_token: str):
        """Connect to a remote bridge."""
        self.config.url = url
        self.config.auth_token = auth_token
        self.config.enabled = True
        self._connected = True
        logger.info(f"Bridge connected to {url}")

    async def disconnect(self):
        """Disconnect from the bridge."""
        if self._poll_task:
            self._poll_task.cancel()
            self._poll_task = None
        self._connected = False
        self.config.enabled = False
        logger.info("Bridge disconnected")

    async def send_message(self, message: dict[str, Any]):
        """Send a message through the bridge."""
        if not self._connected:
            logger.warning("Bridge not connected")
            return
        # Placeholder — would use WebSocket/SSE transport
        logger.debug(f"Bridge send: {message}")

    async def start_polling(self, interval_ms: int = 2000):
        """Start polling for messages."""
        if not self._connected:
            return

        async def poll():
            while self._connected:
                try:
                    # Placeholder — would fetch from bridge endpoint
                    await asyncio.sleep(interval_ms / 1000)
                except asyncio.CancelledError:
                    break

        self._poll_task = asyncio.create_task(poll())

    async def stop_polling(self):
        if self._poll_task:
            self._poll_task.cancel()
            self._poll_task = None


def main() -> None:
    """Entry point for the `vivian-bridge` console script."""
    asyncio.run(bridgeMain(sys.argv[1:]))


if __name__ == "__main__":
    main()

