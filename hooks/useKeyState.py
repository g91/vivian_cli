"""Key state tracking — mirrors src/hooks/useKeyState.ts."""
from __future__ import annotations

def useKeyState() -> dict:
    """Track currently pressed keys."""
    return {
        "pressedKeys": set(),
        "isKeyPressed": lambda key: False,
    }

use_key_state = useKeyState
