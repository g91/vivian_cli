"""ANSI-aware string slicing — mirrors src/utils/sliceAnsi.ts"""
from __future__ import annotations

import re

# Matches ANSI escape sequences
_ANSI_RE = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~]|\][^\x07]*\x07|\][^\x1b]*\x1b\\)")


def _char_width(ch: str) -> int:
    """Return display width of a single character (0, 1, or 2)."""
    try:
        import unicodedata
        eaw = unicodedata.east_asian_width(ch)
        if eaw in ("W", "F"):
            return 2
        if unicodedata.category(ch) in ("Mn", "Me", "Cf"):
            return 0
        return 1
    except Exception:
        return 1


def slice_ansi(s: str, start: int, end: int | None = None) -> str:
    """Slice a string that may contain ANSI codes, counting display cells.

    Mirrors sliceAnsi() from sliceAnsi.ts. The start/end indices are in
    display-cell units (e.g. CJK characters count as 2).
    """
    # Tokenize: split into ANSI escape tokens and text characters
    tokens: list[tuple[str, str]] = []
    pos = 0
    for m in _ANSI_RE.finditer(s):
        if m.start() > pos:
            for ch in s[pos:m.start()]:
                tokens.append(("text", ch))
        tokens.append(("ansi", m.group()))
        pos = m.end()
    for ch in s[pos:]:
        tokens.append(("text", ch))

    result = ""
    open_codes: list[str] = []
    position = 0
    include = False

    for kind, val in tokens:
        width = 0 if kind == "ansi" else _char_width(val)

        if end is not None and position >= end:
            if kind == "ansi" or width > 0 or not include:
                break

        if kind == "ansi":
            open_codes.append(val)
            if include:
                result += val
        else:
            if not include and position >= start:
                if start > 0 and width == 0:
                    continue
                include = True
                # Prepend active codes
                result = "".join(open_codes)
            if include:
                result += val
            position += width

    # Close any open escape sequences
    # For simple SGR codes, append reset if anything was opened
    if open_codes and any(c.startswith("\x1b[") and not c == "\x1b[m" and not c == "\x1b[0m" for c in open_codes):
        result += "\x1b[0m"

    return result
