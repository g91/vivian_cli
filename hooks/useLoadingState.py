"""Loading state — mirrors src/hooks/useLoadingState.ts."""
from __future__ import annotations

def useLoadingState(initialLoading: bool = False) -> dict:
    """Manage loading state."""
    return {
        "loading": initialLoading,
        "setLoading": lambda b: None,
    }

use_loading_state = useLoadingState
