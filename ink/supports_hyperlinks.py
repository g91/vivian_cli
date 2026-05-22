"""Port of src/ink/supports-hyperlinks.ts."""
from __future__ import annotations

import os
import sys
from typing import Any

ADDITIONAL_HYPERLINK_TERMINALS = [
    "ghostty", "Hyper", "kitty", "alacritty",
    "iTerm.app", "iTerm2",
]


def supportsHyperlinks(
    stdout_supported: bool | None = None,
    env: dict[str, str | None] | None = None,
) -> bool:
    if stdout_supported is None:
        stdout_supported = sys.stdout.isatty()
    if stdout_supported:
        return True

    env = env or os.environ

    term_program = env.get("TERM_PROGRAM")
    if term_program and term_program in ADDITIONAL_HYPERLINK_TERMINALS:
        return True

    lc_terminal = env.get("LC_TERMINAL")
    if lc_terminal and lc_terminal in ADDITIONAL_HYPERLINK_TERMINALS:
        return True

    term = env.get("TERM", "")
    if "kitty" in term:
        return True

    return False


supports_hyperlinks = supportsHyperlinks
