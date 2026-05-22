"""Memory usage tracking — mirrors src/hooks/useMemoryUsage.ts."""
from __future__ import annotations

def useMemoryUsage() -> dict:
    """Track memory usage."""
    return {
        "usage": 0,
        "limit": 0,
        "percentage": 0,
    }

use_memory_usage = useMemoryUsage
