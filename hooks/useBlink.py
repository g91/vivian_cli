"""Port of src/hooks/useBlink.ts."""
from __future__ import annotations

import time
from typing import Callable, Tuple

BLINK_INTERVAL_MS = 600


def useBlink(enabled: bool, intervalMs: int = BLINK_INTERVAL_MS) -> Tuple[Callable[[object], None], bool]:
    def ref(_element: object) -> None:
        return None

    if not enabled:
        return ref, True

    now_ms = int(time.time() * 1000)
    is_visible = (now_ms // intervalMs) % 2 == 0
    return ref, is_visible
