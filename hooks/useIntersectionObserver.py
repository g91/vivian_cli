"""Intersection observer — mirrors src/hooks/useIntersectionObserver.ts."""
from __future__ import annotations
from typing import Any, Callable

def useIntersectionObserver(callback: Callable | None = None, options: dict | None = None) -> dict[str, Any]:
    """Observe element visibility."""
    return {
        "ref": None,
        "isVisible": False,
        "callback": callback,
    }

use_intersection_observer = useIntersectionObserver
