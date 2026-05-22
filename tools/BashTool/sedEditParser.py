"""Sed edit command parser — mirrors src/tools/BashTool/sedEditParser.ts."""
from __future__ import annotations
import re
import shlex
from dataclasses import dataclass
from secrets import token_hex
from typing import Optional


@dataclass
class SedEditInfo:
    """Information about a sed in-place edit command."""
    filePath: str
    pattern: str
    replacement: str
    flags: str
    extendedRegex: bool


_BACKSLASH_PLACEHOLDER = "\x00BACKSLASH\x00"
_PLUS_PLACEHOLDER = "\x00PLUS\x00"
_QUESTION_PLACEHOLDER = "\x00QUESTION\x00"
_PIPE_PLACEHOLDER = "\x00PIPE\x00"
_LPAREN_PLACEHOLDER = "\x00LPAREN\x00"
_RPAREN_PLACEHOLDER = "\x00RPAREN\x00"


def isSedInPlaceEdit(command: str) -> bool:
    """Check if a command is a sed in-place edit command."""
    return parseSedEditCommand(command) is not None


def parseSedEditCommand(command: str) -> Optional[SedEditInfo]:
    """
    Parse a sed edit command and extract edit information.
    Returns None if the command is not a valid sed in-place edit.
    """
    trimmed = command.strip()
    if not re.match(r"^\s*sed\s+", trimmed):
        return None

    try:
        tokens = shlex.split(trimmed)[1:]  # Skip "sed"
    except ValueError:
        return None

    hasInPlaceFlag = False
    extendedRegex = False
    expression: Optional[str] = None
    filePath: Optional[str] = None

    i = 0
    while i < len(tokens):
        arg = tokens[i]

        if arg in ("-i", "--in-place"):
            hasInPlaceFlag = True
            i += 1
            # Check for optional backup suffix (empty string or starts with dot)
            if i < len(tokens):
                nextArg = tokens[i]
                if not nextArg.startswith("-") and (nextArg == "" or nextArg.startswith(".")):
                    i += 1  # consume backup suffix
            continue

        if arg in ("-E", "-r", "--regexp-extended"):
            extendedRegex = True
            i += 1
            continue

        if arg in ("-e", "--expression"):
            i += 1
            if i < len(tokens):
                expression = tokens[i]
                i += 1
            continue

        if not arg.startswith("-") and expression is None:
            # Could be the expression or filename
            if re.match(r"^s([^\w\s])", arg):
                expression = arg
            else:
                filePath = arg
            i += 1
            continue

        if not arg.startswith("-") and expression is not None:
            filePath = arg
            i += 1
            continue

        i += 1  # Skip unknown flags

    if not hasInPlaceFlag or expression is None or filePath is None:
        return None

    # Parse s/pattern/replacement/flags
    if not re.match(r"^s.", expression):
        return None

    delim = expression[1]
    # Escape the delimiter for regex
    escaped_delim = re.escape(delim)
    parts = re.split(rf"(?<!\\){escaped_delim}", expression[2:])
    if len(parts) < 2:
        return None

    pattern = parts[0]
    replacement = parts[1] if len(parts) > 1 else ""
    subflags = parts[2] if len(parts) > 2 else ""

    return SedEditInfo(
        filePath=filePath,
        pattern=pattern,
        replacement=replacement,
        flags=subflags,
        extendedRegex=extendedRegex,
    )


def applySedSubstitution(content: str, sedInfo: SedEditInfo) -> str:
    regex_flags = 0
    if "i" in sedInfo.flags or "I" in sedInfo.flags:
        regex_flags |= re.IGNORECASE
    if "m" in sedInfo.flags or "M" in sedInfo.flags:
        regex_flags |= re.MULTILINE

    js_pattern = sedInfo.pattern.replace(r"\/", "/")
    if not sedInfo.extendedRegex:
        js_pattern = (
            js_pattern.replace(r"\\", _BACKSLASH_PLACEHOLDER)
            .replace(r"\+", _PLUS_PLACEHOLDER)
            .replace(r"\?", _QUESTION_PLACEHOLDER)
            .replace(r"\|", _PIPE_PLACEHOLDER)
            .replace(r"\(", _LPAREN_PLACEHOLDER)
            .replace(r"\)", _RPAREN_PLACEHOLDER)
            .replace("+", r"\+")
            .replace("?", r"\?")
            .replace("|", r"\|")
            .replace("(", r"\(")
            .replace(")", r"\)")
            .replace(_BACKSLASH_PLACEHOLDER, r"\\")
            .replace(_PLUS_PLACEHOLDER, "+")
            .replace(_QUESTION_PLACEHOLDER, "?")
            .replace(_PIPE_PLACEHOLDER, "|")
            .replace(_LPAREN_PLACEHOLDER, "(")
            .replace(_RPAREN_PLACEHOLDER, ")")
        )

    replacement = sedInfo.replacement.replace(r"\/", "/")
    amp_placeholder = f"___ESCAPED_AMPERSAND_{token_hex(8)}___"
    replacement = replacement.replace(r"\&", amp_placeholder).replace("&", r"\g<0>").replace(amp_placeholder, "&")

    count = 0 if "g" in sedInfo.flags else 1
    try:
        return re.sub(js_pattern, replacement, content, count=count, flags=regex_flags)
    except re.error:
        return content


__all__ = ["SedEditInfo", "isSedInPlaceEdit", "parseSedEditCommand", "applySedSubstitution"]
