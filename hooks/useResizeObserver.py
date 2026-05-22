"""Resize observer — mirrors src/hooks/useResizeObserver.ts."""
from __future__ import annotations
from typing import Any, Callable

def useResizeObserver(callback: Callable | None = None) -> dict[str, Any]:
    """Observe element resize."""
    return {
        "ref": None,
        "width": 0,
        "height": 0,
        "callback": callback,
    }

use_resize_observer = useResizeObserver
