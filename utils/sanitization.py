"""Unicode sanitization — mirrors src/utils/sanitization.ts"""
from __future__ import annotations

import re
import unicodedata

_MAX_ITERATIONS = 10

# Dangerous Unicode code-point ranges
_DANGEROUS_RANGES = re.compile(
    "[\u200b-\u200f"      # Zero-width spaces, LTR/RTL marks
    "\u202a-\u202e"       # Directional formatting
    "\u2066-\u2069"       # Directional isolates
    "\ufeff"              # Byte order mark
    "\ue000-\uf8ff"       # BMP private use area
    "]"
)

# Format controls, private use, unassigned (Cf, Co, Cn)
_UNICODE_PROPERTY_RE = re.compile(r"[^\S\xa0]")  # fallback: strip invisible


def _strip_dangerous(text: str) -> str:
    """Strip dangerous Unicode code points from a string."""
    # Remove format controls (Cf), private use (Co), and unassigned (Cn)
    result = "".join(
        ch for ch in text
        if unicodedata.category(ch) not in ("Cf", "Co", "Cn")
    )
    # Explicit range strip as defence-in-depth
    result = _DANGEROUS_RANGES.sub("", result)
    return result


def partially_sanitize_unicode(prompt: str) -> str:
    """Iteratively sanitize Unicode in a string until stable or max iterations."""
    current = prompt
    previous = ""
    iterations = 0

    while current != previous and iterations < _MAX_ITERATIONS:
        previous = current
        current = unicodedata.normalize("NFKC", current)
        current = _strip_dangerous(current)
        iterations += 1

    if iterations >= _MAX_ITERATIONS:
        raise ValueError(
            f"Unicode sanitization reached maximum iterations ({_MAX_ITERATIONS}) "
            f"for input: {prompt[:100]}"
        )
    return current


def recursively_sanitize_unicode(value):
    """Recursively sanitize all string values in a nested structure."""
    if isinstance(value, str):
        return partially_sanitize_unicode(value)
    if isinstance(value, list):
        return [recursively_sanitize_unicode(v) for v in value]
    if isinstance(value, dict):
        return {
            recursively_sanitize_unicode(k): recursively_sanitize_unicode(v)
            for k, v in value.items()
        }
    return value
