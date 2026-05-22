"""Port of src/ink/stringWidth.ts."""
from __future__ import annotations

import re
import unicodedata

_EMOJI_REGEX = re.compile(
    "[\U0001F300-\U0001FAFF"  # Misc symbols, emoticons, etc.
    "\U00002600-\U000027BF"   # Misc symbols
    "\U0001F1E6-\U0001F1FF"   # Regional indicators
    "]"
)

def _east_asian_width(cp: int) -> int:
    """Get East Asian Width: 0=neutral/narrow, 1=wide, 2=ambiguous."""
    try:
        ea = unicodedata.east_asian_width(chr(cp))
    except ValueError:
        return 0
    if ea in ("W", "F"):
        return 2
    return 1


def _is_zero_width(cp: int) -> bool:
    if cp <= 0x1F or (0x7F <= cp <= 0x9F):
        return True
    if 0x200B <= cp <= 0x200D:
        return True
    if cp == 0xFEFF:
        return True
    if 0x2060 <= cp <= 0x2064:
        return True
    if 0xFE00 <= cp <= 0xFE0F or 0xE0100 <= cp <= 0xE01EF:
        return True
    if 0x0300 <= cp <= 0x036F or 0x1AB0 <= cp <= 0x1AFF:
        return True
    if 0x1DC0 <= cp <= 0x1DFF or 0x20D0 <= cp <= 0x20FF:
        return True
    if 0xFE20 <= cp <= 0xFE2F:
        return True
    if cp == 0x00AD:
        return True
    if 0xD800 <= cp <= 0xDFFF:
        return True
    if 0xE0000 <= cp <= 0xE007F:
        return True
    return False


def _needs_segmentation(s: str) -> bool:
    for ch in s:
        cp = ord(ch)
        if 0x1F300 <= cp <= 0x1FAFF:
            return True
        if 0x2600 <= cp <= 0x27BF:
            return True
        if 0x1F1E6 <= cp <= 0x1F1FF:
            return True
        if 0xFE00 <= cp <= 0xFE0F:
            return True
        if cp == 0x200D:
            return True
    return False


def _get_emoji_width(grapheme: str) -> int:
    first = ord(grapheme[0])
    if 0x1F1E6 <= first <= 0x1F1FF:
        return 1 if len(grapheme) == 1 else 2
    if len(grapheme) == 2:
        second = ord(grapheme[1])
        if second == 0xFE0F and (
            (0x30 <= first <= 0x39) or first in (0x23, 0x2A)
        ):
            return 1
    return 2


def stringWidth(s: str) -> int:
    if not s:
        return 0

    # Fast path: pure ASCII
    is_ascii = all(ord(c) < 127 and ord(c) != 0x1B for c in s)
    if is_ascii:
        return sum(1 for c in s if ord(c) > 0x1F)

    # Strip ANSI
    if "\x1b" in s:
        s = re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", s)
        s = re.sub(r"\x1b\][^\x07]*\x07", "", s)
        if not s:
            return 0

    if not _needs_segmentation(s):
        width = 0
        for ch in s:
            cp = ord(ch)
            if not _is_zero_width(cp):
                width += _east_asian_width(cp)
        return width

    # Grapheme-aware measurement
    width = 0
    import regex
    for grapheme in regex.findall(r'\X', s):
        if _EMOJI_REGEX.search(grapheme):
            width += _get_emoji_width(grapheme)
            continue
        for ch in grapheme:
            cp = ord(ch)
            if not _is_zero_width(cp):
                width += _east_asian_width(cp)
                break
    return width


string_width = stringWidth
