"""Keyboard shortcut hint component — mirrors src/components/design-system/KeyboardShortcutHint.tsx."""

from __future__ import annotations


def KeyboardShortcutHint(shortcut: str, action: str, parens: bool = False, bold: bool = False) -> str:
    shortcut_text = f"**{shortcut}**" if bold else shortcut
    body = f"{shortcut_text} to {action}"
    return f"({body})" if parens else body


__all__ = ["KeyboardShortcutHint"]