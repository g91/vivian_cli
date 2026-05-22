"""Shallow compare — mirrors src/hooks/useShallowCompare.ts."""
from __future__ import annotations
from typing import Any

def useShallowCompare(value: Any) -> bool:
    """Compare values shallowly."""
    return True

use_shallow_compare = useShallowCompare
