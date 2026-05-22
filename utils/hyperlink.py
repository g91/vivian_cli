"""Hyperlink utilities — mirrors src/utils/hyperlink.ts"""
from __future__ import annotations

import os
from typing import Any

# OSC 8 hyperlink escape sequences
OSC8_START = "\x1b]8;;"
OSC8_END = "\x07"


def _supports_hyperlinks() -> bool:
    """Check if the terminal supports OSC 8 hyperlinks."""
    term = os.environ.get("TERM", "")
    term_program = os.environ.get("TERM_PROGRAM", "")
    colorterm = os.environ.get("COLORTERM", "")
    # Known supporting terminals
    if term_program in ("iTerm.app", "WezTerm", "Hyper"):
        return True
    if os.environ.get("VTE_VERSION"):
        return True
    if "xterm-kitty" in term:
        return True
    # Fallback: check COLORTERM
    return colorterm in ("truecolor", "24bit")


def supports_hyperlinks() -> bool:
    return _supports_hyperlinks()


def create_hyperlink(
    url: str,
    content: str | None = None,
    options: dict[str, Any] | None = None,
) -> str:
    """Create an OSC 8 hyperlink if supported, otherwise return the URL.

    Mirrors createHyperlink() from hyperlink.ts.
    """
    has_support = options.get("supportsHyperlinks") if isinstance(options, dict) else None
    if has_support is None:
        has_support = _supports_hyperlinks()
    if not has_support:
        return url
    display_text = content or url
    return f"{OSC8_START}{url}{OSC8_END}{display_text}{OSC8_START}{OSC8_END}"


createHyperlink = create_hyperlink
supportsHyperlinks = supports_hyperlinks
