"""Cost summary exit hook mirroring src/costHook.ts."""

from __future__ import annotations

import atexit
import sys
from typing import Any, Callable, Optional

from .cost_tracker import formatTotalCost, saveCurrentSessionCosts
from .utils.billing import has_console_billing_access


_registered_callbacks: dict[int, Callable[[], None]] = {}


def useCostSummary(
    getFpsMetrics: Optional[Callable[[], Any]] = None,
) -> Callable[[], None]:
    def _on_exit() -> None:
        if has_console_billing_access():
            sys.stdout.write("\n" + formatTotalCost() + "\n")
        saveCurrentSessionCosts(getFpsMetrics() if getFpsMetrics is not None else None)

    callback_id = id(_on_exit)
    _registered_callbacks[callback_id] = _on_exit
    atexit.register(_on_exit)

    def _cleanup() -> None:
        callback = _registered_callbacks.pop(callback_id, None)
        if callback is None:
            return
        try:
            atexit.unregister(callback)
        except Exception:
            pass

    return _cleanup


use_cost_summary = useCostSummary


__all__ = ["useCostSummary", "use_cost_summary"]