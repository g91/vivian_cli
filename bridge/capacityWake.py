"""Port of src/bridge/capacityWake.ts

Shared capacity-wake primitive for bridge poll loops.
Both replBridge and bridgeMain need to sleep while at capacity but wake
early when either (a) the outer loop signal aborts, or (b) capacity frees up.
"""
from __future__ import annotations

import asyncio
from typing import Callable, Optional


class CapacitySignal:
    """Merged abort event + cleanup callable."""

    def __init__(self, event: asyncio.Event, cleanup: Callable[[], None]):
        self.event = event
        self.cleanup = cleanup

    async def wait_aborted(self) -> None:
        """Wait until the signal fires (outer abort or wake)."""
        await self.event.wait()


class CapacityWake:
    """Wake controller that merges an outer stop event with an inner wake event."""

    def __init__(self, outer_event: asyncio.Event):
        self._outer = outer_event
        self._wake_event = asyncio.Event()

    def signal(self) -> CapacitySignal:
        """Return a merged event that fires when outer stops or wake() is called."""
        merged = asyncio.Event()
        fired = False

        async def _watch():
            nonlocal fired
            # Wait for either outer or wake
            done, pending = await asyncio.wait(
                [
                    asyncio.ensure_future(self._outer.wait()),
                    asyncio.ensure_future(self._wake_event.wait()),
                ],
                return_when=asyncio.FIRST_COMPLETED,
            )
            for p in pending:
                p.cancel()
            if not fired:
                fired = True
                merged.set()

        asyncio.ensure_future(_watch())

        def cleanup():
            nonlocal fired
            fired = True
            merged.set()

        return CapacitySignal(merged, cleanup)

    def wake(self) -> None:
        """Abort current at-capacity sleep and arm a fresh event."""
        self._wake_event.set()
        self._wake_event = asyncio.Event()


def createCapacityWake(outer_event: asyncio.Event) -> CapacityWake:
    return CapacityWake(outer_event)
