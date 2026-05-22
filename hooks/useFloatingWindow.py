"""Floating window — mirrors src/hooks/useFloatingWindow.ts."""
from __future__ import annotations
from typing import Any

def useFloatingWindow() -> dict[str, Any]:
    """Manage floating window."""
    return {
        "x": 0,
        "y": 0,
        "width": 400,
        "height": 300,
        "visible": False,
        "move": lambda x, y: None,
        "resize": lambda w, h: None,
    }

use_floating_window = useFloatingWindow
