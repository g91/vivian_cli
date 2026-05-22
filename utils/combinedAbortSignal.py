"""Combined abort signal — mirrors src/utils/combinedAbortSignal.ts"""
from __future__ import annotations

import threading
from typing import Callable, Optional

from .abortController import AbortController, AbortSignal, create_abort_controller


def create_combined_abort_signal(
    signal: Optional[AbortSignal] = None,
    *,
    signal_b: Optional[AbortSignal] = None,
    timeout_ms: Optional[float] = None,
) -> tuple["AbortSignal", Callable[[], None]]:
    """Create a combined AbortSignal that aborts when any input signal aborts or timeout elapses.

    Returns (combined_signal, cleanup_fn).
    Mirrors createCombinedAbortSignal() from combinedAbortSignal.ts.
    """
    combined = create_abort_controller()

    if (signal and signal.aborted) or (signal_b and signal_b.aborted):
        combined.abort()
        return combined.signal, lambda: None

    timer: list[Optional[threading.Timer]] = [None]

    def _abort():
        if timer[0] is not None:
            timer[0].cancel()
            timer[0] = None
        combined.abort()

    if timeout_ms is not None:
        t = threading.Timer(timeout_ms / 1000, _abort)
        t.daemon = True
        t.start()
        timer[0] = t

    if signal:
        signal.add_event_listener("abort", _abort)
    if signal_b:
        signal_b.add_event_listener("abort", _abort)

    def cleanup() -> None:
        if timer[0] is not None:
            timer[0].cancel()
            timer[0] = None
        if signal:
            signal.remove_event_listener("abort", _abort)
        if signal_b:
            signal_b.remove_event_listener("abort", _abort)

    return combined.signal, cleanup
