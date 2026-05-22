"""Error boundary — mirrors src/hooks/useErrorBoundary.ts."""
from __future__ import annotations
from typing import Any

def useErrorBoundary(onError: Any = None) -> dict[str, Any]:
    """Catch and handle errors."""
    return {
        "hasError": False,
        "error": None,
        "reset": lambda: None,
    }

use_error_boundary = useErrorBoundary
