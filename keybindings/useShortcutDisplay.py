"""Shortcut display helper — mirrors src/keybindings/useShortcutDisplay.ts."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..services.analytics.index import logEvent


@runtime_checkable
class _KeybindingDisplayContext(Protocol):
    def getDisplayText(self, action: str, context: str) -> str | None:
        ...


_LOGGED_FALLBACKS: set[str] = set()


def useShortcutDisplay(
    action: str,
    context: str,
    fallback: str,
    keybinding_context: _KeybindingDisplayContext | None = None,
) -> str:
    resolved = None
    if keybinding_context is not None:
        resolved = keybinding_context.getDisplayText(action, context)
    is_fallback = resolved is None
    reason = "action_not_found" if keybinding_context is not None else "no_context"

    if is_fallback:
        key = f"{action}:{context}:{reason}"
        if key not in _LOGGED_FALLBACKS:
            _LOGGED_FALLBACKS.add(key)
            logEvent(
                "tengu_keybinding_fallback_used",
                {
                    "action": action,
                    "context": context,
                    "fallback": fallback,
                    "reason": reason,
                },
            )
        return fallback
    return resolved


use_shortcut_display = useShortcutDisplay