"""Port of src/ink/hooks/use-animation-frame.ts."""
from __future__ import annotations

from typing import Callable

from ..components.ClockContext import getClockContext
from ..components.StdinContext import getStdinContext


def useAnimationFrame(callback: Callable[[], None], intervalMs: int | None = 16) -> Callable[[], None]:
    """Register an animation-frame style callback."""
    if intervalMs is None:
        return lambda: None
    clock = getClockContext()
    stdin_context = getStdinContext()
    app = stdin_context.app
    if app is not None and hasattr(app, "registerInterval"):
        return app.registerInterval(callback, intervalMs, repeat=True)
    if clock is None:
        return lambda: None
    return clock.subscribe(callback, keepAlive=True)


use_animation_frame = useAnimationFrame
