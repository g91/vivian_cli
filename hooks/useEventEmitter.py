"""Event emitter — mirrors src/hooks/useEventEmitter.ts."""
from __future__ import annotations
from typing import Any, Callable

def useEventEmitter() -> dict[str, Any]:
    """Publish-subscribe event system."""
    listeners = {}
    
    def on(event: str, callback: Callable) -> None:
        if event not in listeners:
            listeners[event] = []
        listeners[event].append(callback)
    
    def emit(event: str, *args: Any) -> None:
        if event in listeners:
            for cb in listeners[event]:
                cb(*args)
    
    def off(event: str, callback: Callable) -> None:
        if event in listeners:
            listeners[event] = [cb for cb in listeners[event] if cb is not callback]
    
    return {"on": on, "emit": emit, "off": off}

use_event_emitter = useEventEmitter
