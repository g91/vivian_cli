"""Retry logic — mirrors src/hooks/useRetry.ts."""
from __future__ import annotations
from typing import Any, Callable

def useRetry(fn: Callable, maxRetries: int = 3) -> dict[str, Any]:
    """Execute with automatic retries."""
    retries = 0
    
    async def execute() -> Any:
        nonlocal retries
        for attempt in range(maxRetries):
            try:
                return await fn()
            except Exception as e:
                retries = attempt + 1
                if attempt == maxRetries - 1:
                    raise
    
    return {"execute": execute, "retries": retries}

use_retry = useRetry
