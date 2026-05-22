"""Prevent default — mirrors src/hooks/usePreventDefault.ts."""
from __future__ import annotations

def usePreventDefault(eventType: str = "click") -> callable:
    """Prevent default event behavior."""
    return lambda e: None

use_prevent_default = usePreventDefault
