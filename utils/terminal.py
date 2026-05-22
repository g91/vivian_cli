"""Port of src/utils/terminal.ts."""
from __future__ import annotations

from typing import Dict
import re
import unicodedata

from .sliceAnsi import slice_ansi


MAX_LINES_TO_SHOW = 3
PADDING_TO_PREVENT_OVERFLOW = 10
_ANSI_ESCAPE_RE = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~]|\][^\x07]*\x07|\][^\x1b]*\x1b\\)")


def _ctrl_o_to_expand() -> str:
    return "(ctrl+o to expand)"


def _dim(text: str) -> str:
    return f"\x1b[2m{text}\x1b[0m"


def _strip_ansi(text: str) -> str:
    return _ANSI_ESCAPE_RE.sub("", text)


def _string_width(text: str) -> int:
    width = 0
    for char in _strip_ansi(text):
        if unicodedata.category(char) in ("Mn", "Me", "Cf"):
            continue
        width += 2 if unicodedata.east_asian_width(char) in ("W", "F") else 1
    return width


def wrapText(text, wrapWidth):
    """Inserts newlines in a string to wrap it at the specified width."""
    lines = text.split("\n")
    wrapped_lines = []

    for line in lines:
        visible_width = _string_width(line)
        if visible_width <= wrapWidth:
            wrapped_lines.append(line.rstrip())
        else:
            position = 0
            while position < visible_width:
                chunk = slice_ansi(line, position, position + wrapWidth)
                wrapped_lines.append(chunk.rstrip())
                position += wrapWidth

    remaining_lines = len(wrapped_lines) - MAX_LINES_TO_SHOW
    if remaining_lines == 1:
        return {
            "aboveTheFold": "\n".join(wrapped_lines[: MAX_LINES_TO_SHOW + 1]).rstrip(),
            "remainingLines": 0,
        }

    return {
        "aboveTheFold": "\n".join(wrapped_lines[:MAX_LINES_TO_SHOW]).rstrip(),
        "remainingLines": max(0, remaining_lines),
    }


def renderTruncatedContent(content, terminalWidth, suppressExpandHint=False):
    """Renders the content with line-based truncation for terminal display."""
    trimmed_content = str(content).rstrip()
    if not trimmed_content:
        return ""

    wrap_width = max(terminalWidth - PADDING_TO_PREVENT_OVERFLOW, 10)
    max_chars = MAX_LINES_TO_SHOW * wrap_width * 4
    pre_truncated = len(trimmed_content) > max_chars
    content_for_wrapping = (
        trimmed_content[:max_chars] if pre_truncated else trimmed_content
    )

    wrapped = wrapText(content_for_wrapping, wrap_width)
    above_the_fold = wrapped["aboveTheFold"]
    remaining_lines = wrapped["remainingLines"]

    estimated_remaining = (
        max(remaining_lines, -(-len(trimmed_content) // wrap_width) - MAX_LINES_TO_SHOW)
        if pre_truncated
        else remaining_lines
    )

    parts = [above_the_fold]
    if estimated_remaining > 0:
        suffix = "" if suppressExpandHint else f" {_ctrl_o_to_expand()}"
        parts.append(_dim(f"... +{estimated_remaining} lines{suffix}"))
    return "\n".join(part for part in parts if part)


def isOutputLineTruncated(content):
    pos = 0
    for _ in range(MAX_LINES_TO_SHOW + 1):
        pos = content.find("\n", pos)
        if pos == -1:
            return False
        pos += 1
    return pos < len(content)


wrap_text = wrapText
render_truncated_content = renderTruncatedContent
is_output_line_truncated = isOutputLineTruncated

