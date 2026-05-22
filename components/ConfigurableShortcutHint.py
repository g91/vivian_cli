"""Configurable shortcut hint — minimal port of src/components/ConfigurableShortcutHint.tsx."""

from __future__ import annotations


def ConfigurableShortcutHint(
    action: str,
    context: str,
    fallback: str,
    description: str,
    parens: bool = False,
    bold: bool = False,
) -> str:
    from .design_system.KeyboardShortcutHint import KeyboardShortcutHint

    del action, context
    return KeyboardShortcutHint(shortcut=fallback, action=description, parens=parens, bold=bold)


__all__ = ["ConfigurableShortcutHint"]