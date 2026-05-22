"""Port of src/ink/wrapAnsi.ts."""
from __future__ import annotations

import re
from .stringWidth import stringWidth


def wrapAnsi(text: str, columns: int, hard: bool = False, trim: bool = False, wordWrap: bool = True) -> str:
    """Wrap text with ANSI codes to a given width."""
    if columns <= 0:
        return text

    lines = text.split("\n")
    result: list[str] = []

    for line in lines:
        if stringWidth(line) <= columns:
            result.append(line)
            continue

        wrapped = _wrap_line(line, columns, hard, trim, wordWrap)
        result.append(wrapped)

    return "\n".join(result)


def _wrap_line(line: str, columns: int, hard: bool, trim: bool, wordWrap: bool) -> str:
    """Wrap a single line."""
    # Tokenize into ANSI and text segments
    segments = _tokenize_ansi(line)
    wrapped_lines: list[str] = []
    current_line = ""
    current_width = 0
    active_styles = ""

    for seg_type, seg_value in segments:
        if seg_type == "ansi":
            active_styles += seg_value
            continue

        # Text segment - may need wrapping
        words = seg_value.split(" ") if wordWrap else [seg_value]
        for wi, word in enumerate(words):
            word_width = stringWidth(word)

            if wi > 0 and wordWrap:
                # Check if adding space + word fits
                if current_width + 1 + word_width > columns and current_width > 0:
                    wrapped_lines.append(active_styles + current_line + "\x1b[0m")
                    current_line = ""
                    current_width = 0

                if current_width > 0:
                    current_line += " "
                    current_width += 1

            # If word itself is too long, hard-break it
            if hard and word_width > columns:
                while word_width > columns:
                    # Find break point
                    part, word, word_width = _hard_break(word, columns, word_width)
                    current_line += part
                    wrapped_lines.append(active_styles + current_line + "\x1b[0m")
                    current_line = ""
                    current_width = 0
                if word:
                    current_line = word
                    current_width = word_width
            else:
                if current_width + word_width > columns and current_width > 0:
                    wrapped_lines.append(active_styles + current_line + "\x1b[0m")
                    current_line = word
                    current_width = word_width
                else:
                    current_line += word
                    current_width += word_width

    if current_line:
        wrapped_lines.append(active_styles + current_line + "\x1b[0m")

    return "\n".join(wrapped_lines) if wrapped_lines else ""


def _tokenize_ansi(text: str) -> list[tuple[str, str]]:
    """Split text into (type, value) tuples: ('text', ...) or ('ansi', ...)."""
    segments: list[tuple[str, str]] = []
    i = 0
    buf = ""

    while i < len(text):
        if text[i] == "\x1b" and i + 1 < len(text) and text[i + 1] == "[":
            if buf:
                segments.append(("text", buf))
                buf = ""
            j = i + 2
            while j < len(text) and not (0x40 <= ord(text[j]) <= 0x7E):
                j += 1
            if j < len(text):
                j += 1
            segments.append(("ansi", text[i:j]))
            i = j
        else:
            buf += text[i]
            i += 1

    if buf:
        segments.append(("text", buf))

    return segments


def _hard_break(word: str, columns: int, word_width: int) -> tuple[str, str, int]:
    """Break a word at column boundary."""
    part = ""
    part_width = 0
    for ch in word:
        chw = stringWidth(ch)
        if part_width + chw > columns:
            break
        part += ch
        part_width += chw
    rest = word[len(part):]
    rest_width = stringWidth(rest)
    return part, rest, rest_width


wrap_ansi = wrapAnsi
