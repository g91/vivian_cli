"""Cancel request hook — mirrors src/hooks/useCancelRequest.ts."""
from __future__ import annotations
from typing import Callable

def useCancelRequest(onCancel: Callable[[], None] | None = None) -> dict:
    """Manage request cancellation."""
    cancelled = False
    
    def cancel() -> None:
        nonlocal cancelled
        cancelled = True
        if onCancel:
            onCancel()
    
    def isCancelled() -> bool:
        return cancelled
    
    return {'cancel': cancel, 'isCancelled': isCancelled}

use_cancel_request = useCancelRequest
