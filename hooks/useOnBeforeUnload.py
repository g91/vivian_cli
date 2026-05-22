"""On before unload — mirrors src/hooks/useOnBeforeUnload.ts.

In Python, this registers cleanup handlers that execute when the program exits
or when the application is shutting down. Similar to React's beforeunload event.
"""
from __future__ import annotations
import atexit
from typing import Callable, Optional

_unload_handlers: list[Callable[[], None]] = []

def useOnBeforeUnload(handler: Optional[Callable[[], None]] = None) -> Optional[Callable[[], None]]:
    """Register a handler to be called when the application is unloading/exiting.
    
    Args:
        handler: Callback function to execute on unload
        
    Returns:
        Function to unregister the handler, or None if no handler provided
    """
    if handler is None:
        return None
    
    _unload_handlers.append(handler)
    
    # Register with atexit to ensure it runs
    def _run_all_handlers() -> None:
        for h in list(_unload_handlers):
            try:
                h()
            except Exception:
                pass  # Silently ignore errors during shutdown
    
    # Register only once
    if len(_unload_handlers) == 1:
        atexit.register(_run_all_handlers)
    
    # Return unsubscribe function
    def unsubscribe() -> None:
        if handler in _unload_handlers:
            _unload_handlers.remove(handler)
    
    return unsubscribe

use_on_before_unload = useOnBeforeUnload
