"""Shortcut display formatting — mirrors src/keybindings/shortcutFormat.ts."""
from __future__ import annotations

from ..services.analytics.index import logEvent
from .loadUserBindings import loadKeybindingsSync
from .resolver import getBindingDisplayText


LOGGED_FALLBACKS: set[str] = set()


def getShortcutDisplay(action: str, context: str, fallback: str) -> str:
    bindings = loadKeybindingsSync()
    resolved = getBindingDisplayText(action, context, bindings)
    if resolved is None:
        key = f"{action}:{context}"
        if key not in LOGGED_FALLBACKS:
            LOGGED_FALLBACKS.add(key)
            logEvent(
                "tengu_keybinding_fallback_used",
                {
                    "action": action,
                    "context": context,
                    "fallback": fallback,
                    "reason": "action_not_found",
                },
            )
        return fallback
    return resolved


get_shortcut_display = getShortcutDisplay