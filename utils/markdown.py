"""Markdown rendering utilities — mirrors src/utils/markdown.ts"""
from __future__ import annotations

import re
from typing import Optional


def strip_ansi(text: str) -> str:
    """Strip ANSI escape sequences from text."""
    ansi_escape = re.compile(r"\x1b\[[0-9;]*[mGKHF]")
    return ansi_escape.sub("", text)


def apply_markdown(content: str, *, plain: bool = False) -> str:
    """Convert markdown content to terminal-friendly text.

    When plain=True, strips all formatting. Otherwise attempts to apply
    basic terminal formatting where possible.
    """
    if plain:
        # Strip markdown formatting
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", content)  # bold
        text = re.sub(r"\*(.+?)\*", r"\1", text)          # italic
        text = re.sub(r"`(.+?)`", r"\1", text)             # inline code
        text = re.sub(r"#{1,6}\s+", "", text)              # headings
        return text.strip()
    return content


def strip_markdown(text: str) -> str:
    """Strip all markdown formatting from text."""
    return apply_markdown(text, plain=True)
