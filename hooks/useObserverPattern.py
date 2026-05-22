"""Observer pattern — mirrors src/hooks/useObserverPattern.ts."""
from __future__ import annotations
from typing import Any, Callable

def useObserverPattern() -> dict[str, Any]:
    """Observable subscription management."""
    observers = []
    
    def subscribe(callback: Callable) -> Callable:
        observers.append(callback)
        return lambda: observers.remove(callback) if callback in observers else None
    
    def notify(data: Any) -> None:
        for obs in observers:
            obs(data)
    
    return {
        "subscribe": subscribe,
        "notify": notify,
    }

use_observer_pattern = useObserverPattern
