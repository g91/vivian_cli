"""
Port of src/utils/modifiers.ts
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
import importlib
import platform


ModifierKey = str
_PREWARMED = False


def prewarmModifiers():
    """Pre-warm the native module by loading it in advance.
Call this early to avoid delay on first use."""
    global _PREWARMED
    if _PREWARMED or platform.system() != 'Darwin':
        return None
    _PREWARMED = True
    try:
        module = importlib.import_module('modifiers_napi')
        prewarm = getattr(module, 'prewarm', None)
        if callable(prewarm):
            prewarm()
    except Exception:
        return None
    return None


def isModifierPressed(modifier):
    """Check if a specific modifier key is currently pressed (synchronous)."""
    if platform.system() != 'Darwin':
        return False
    module = importlib.import_module('modifiers_napi')
    native_is_modifier_pressed = getattr(module, 'isModifierPressed', None)
    if not callable(native_is_modifier_pressed):
        return False
    return bool(native_is_modifier_pressed(modifier))


prewarm_modifiers = prewarmModifiers
is_modifier_pressed = isModifierPressed

