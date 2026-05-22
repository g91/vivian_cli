"""Vim input — mirrors src/hooks/useVimInput.ts."""
from __future__ import annotations

def useVimInput() -> dict:
    """Vim input mode."""
    return {"mode": "normal"}

use_vim_input = useVimInput
