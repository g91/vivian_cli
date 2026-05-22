"""Port of src/ink/hooks/use-interval.ts."""
from __future__ import annotations

from typing import Callable

from ..components.ClockContext import getClockContext
from ..components.StdinContext import getStdinContext


def useInterval(callback: Callable[[], None], intervalMs: int | None) -> Callable[[], None]:
    """Register an interval callback against the current runtime."""
    if intervalMs is None:
        return lambda: None
    stdin_context = getStdinContext()
    app = stdin_context.app
    if app is not None and hasattr(app, "registerInterval"):
        return app.registerInterval(callback, intervalMs, repeat=True)
    clock = getClockContext()
    if clock is None:
        return lambda: None

    last_run = clock.now()

    def on_tick() -> None:
        nonlocal last_run
        now = clock.now()
        if now - last_run >= intervalMs:
            last_run = now
            callback()

    return clock.subscribe(on_tick, keepAlive=False)


use_interval = useInterval
