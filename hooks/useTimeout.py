"""Port of src/hooks/useTimeout.ts."""
from __future__ import annotations

import time


def useTimeout(delay: int, resetTrigger: int | None = None) -> bool:
    del resetTrigger
    start = time.time() * 1000
    return (time.time() * 1000 - start) >= delay
