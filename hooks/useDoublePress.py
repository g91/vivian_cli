"""Port of src/hooks/useDoublePress.ts."""
from __future__ import annotations

import threading
import time
from typing import Callable, Optional

DOUBLE_PRESS_TIMEOUT_MS = 800


def useDoublePress(
    setPending: Callable[[bool], None],
    onDoublePress: Callable[[], None],
    onFirstPress: Optional[Callable[[], None]] = None,
) -> Callable[[], None]:
    last_press = 0.0
    timeout: list[Optional[threading.Timer]] = [None]

    def clear_timeout_safe() -> None:
        t = timeout[0]
        if t is not None:
            t.cancel()
            timeout[0] = None

    def handler() -> None:
        nonlocal last_press
        now = time.time() * 1000
        time_since_last = now - last_press
        is_double = time_since_last <= DOUBLE_PRESS_TIMEOUT_MS and timeout[0] is not None

        if is_double:
            clear_timeout_safe()
            setPending(False)
            onDoublePress()
        else:
            if onFirstPress is not None:
                onFirstPress()
            setPending(True)
            clear_timeout_safe()

            def clear_pending() -> None:
                setPending(False)
                timeout[0] = None

            timer = threading.Timer(DOUBLE_PRESS_TIMEOUT_MS / 1000.0, clear_pending)
            timeout[0] = timer
            timer.daemon = True
            timer.start()

        last_press = now

    return handler
