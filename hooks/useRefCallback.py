"""Ref callback — mirrors src/hooks/useRefCallback.ts."""
from __future__ import annotations
from typing import Any, Callable

def useRefCallback(callback: Callable[[Any], None] | None = None) -> Callable:
    """Ref callback with trigger."""
    def ref_fn(el: Any) -> None:
        if callback:
            callback(el)
    return ref_fn

use_ref_callback = useRefCallback
