"""String utilities — mirrors src/utils/stringUtils.ts"""
from __future__ import annotations

import re

MAX_STRING_LENGTH = 2 ** 25  # ~33MB


def escape_regexp(s: str) -> str:
    """Escape special regex characters so the string can be used as a literal pattern."""
    return re.escape(s)


def capitalize(s: str) -> str:
    """Uppercase the first character without changing the rest.
    Unlike Python's str.capitalize(), this does NOT lowercase remaining chars.
    """
    if not s:
        return s
    return s[0].upper() + s[1:]


def plural(n: int, word: str, plural_word: str | None = None) -> str:
    """Return singular or plural form of a word based on count."""
    if plural_word is None:
        plural_word = word + "s"
    return word if n == 1 else plural_word


def first_line_of(s: str) -> str:
    """Return the first line of a string without allocating a split array."""
    nl = s.find("\n")
    return s if nl == -1 else s[:nl]


def count_char_in_string(s: str, char: str, start: int = 0) -> int:
    """Count occurrences of `char` in `s` starting from `start`."""
    count = 0
    i = s.find(char, start)
    while i != -1:
        count += 1
        i = s.find(char, i + 1)
    return count


def normalize_full_width_digits(s: str) -> str:
    """Normalize full-width (zenkaku) digits to half-width digits."""
    result = []
    for ch in s:
        cp = ord(ch)
        if 0xFF10 <= cp <= 0xFF19:  # ０-９
            result.append(chr(cp - 0xFEE0))
        else:
            result.append(ch)
    return "".join(result)


def normalize_full_width_space(s: str) -> str:
    """Normalize full-width (U+3000) space to half-width space."""
    return s.replace("\u3000", " ")


def safe_join_lines(
    lines: list[str],
    delimiter: str = ",",
    max_size: int = MAX_STRING_LENGTH,
) -> str:
    """Join strings with a delimiter, truncating if the result exceeds max_size."""
    truncation_marker = "...[truncated]"
    result = ""
    for line in lines:
        sep = delimiter if result else ""
        addition = sep + line
        if len(result) + len(addition) <= max_size:
            result += addition
        else:
            remaining = max_size - len(result) - len(sep) - len(truncation_marker)
            if remaining > 0:
                result += sep + line[:remaining] + truncation_marker
            else:
                result += truncation_marker
            return result
    return result


def truncate_to_lines(text: str, max_lines: int) -> str:
    """Truncate text to at most `max_lines` lines, appending … if truncated."""
    lines = text.split("\n")
    if len(lines) <= max_lines:
        return text
    return "\n".join(lines[:max_lines]) + "…"


class EndTruncatingAccumulator:
    """String accumulator that truncates from the end when size limit is exceeded.
    Mirrors EndTruncatingAccumulator from stringUtils.ts.
    """

    def __init__(self, max_size: int = MAX_STRING_LENGTH) -> None:
        self._content = ""
        self._is_truncated = False
        self._total_bytes_received = 0
        self._max_size = max_size

    def append(self, data: str | bytes) -> None:
        s = data.decode() if isinstance(data, bytes) else data
        self._total_bytes_received += len(s)
        if self._is_truncated and len(self._content) >= self._max_size:
            return
        if len(self._content) + len(s) > self._max_size:
            remaining = self._max_size - len(self._content)
            if remaining > 0:
                self._content += s[:remaining]
            self._is_truncated = True
        else:
            self._content += s

    def __str__(self) -> str:
        if not self._is_truncated:
            return self._content
        truncated_bytes = self._total_bytes_received - self._max_size
        truncated_kb = round(truncated_bytes / 1024)
        return self._content + f"\n... [output truncated - {truncated_kb}KB removed]"

    def clear(self) -> None:
        self._content = ""
        self._is_truncated = False
        self._total_bytes_received = 0

    @property
    def length(self) -> int:
        return len(self._content)

    @property
    def truncated(self) -> bool:
        return self._is_truncated

    @property
    def total_bytes(self) -> int:
        return self._total_bytes_received
