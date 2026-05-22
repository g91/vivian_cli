"""Non-interactive mode — mirrors src/hooks/useNonInteractiveMode.ts."""
from __future__ import annotations

def useNonInteractiveMode() -> bool:
    """Check if running in non-interactive mode."""
    return False

use_non_interactive_mode = useNonInteractiveMode
