"""Port of src/ink/events/dispatcher.ts."""
from __future__ import annotations

from typing import Any


class Dispatcher:
    def __init__(self) -> None:
        self.currentUpdatePriority: int = 0
        self.currentEvent: Any = None
        self.discreteUpdates: Any = None

    def resolveEventPriority(self) -> int:
        return 0
