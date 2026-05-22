"""Vim text object helpers — mirrors src/vim/textObjects.ts."""
from __future__ import annotations

from typing import Callable

TextObjectRange = dict[str, int] | None

PAIRS: dict[str, tuple[str, str]] = {
    "(": ("(", ")"),
    ")": ("(", ")"),
    "b": ("(", ")"),
    "[": ("[", "]"),
    "]": ("[", "]"),
    "{": ("{", "}"),
    "}": ("{", "}"),
    "B": ("{", "}"),
    "<": ("<", ">"),
    ">": ("<", ">"),
    '"': ('"', '"'),
    "'": ("'", "'"),
    "`": ("`", "`"),
}


def isVimWhitespace(ch: str) -> bool:
    return ch.isspace()


def isVimWordChar(ch: str) -> bool:
    return ch.isalnum() or ch == "_"


def isVimPunctuation(ch: str) -> bool:
    return bool(ch) and not isVimWhitespace(ch) and not isVimWordChar(ch)


def findTextObject(
    text: str,
    offset: int,
    objectType: str,
    isInner: bool,
) -> TextObjectRange:
    if not text:
        return None
    offset = max(0, min(offset, len(text) - 1))

    if objectType == "w":
        return findWordObject(text, offset, isInner, isVimWordChar)
    if objectType == "W":
        return findWordObject(text, offset, isInner, lambda ch: not isVimWhitespace(ch))

    pair = PAIRS.get(objectType)
    if pair is None:
        return None
    open_char, close_char = pair
    if open_char == close_char:
        return findQuoteObject(text, offset, open_char, isInner)
    return findBracketObject(text, offset, open_char, close_char, isInner)


def findWordObject(
    text: str,
    offset: int,
    isInner: bool,
    isWordChar: Callable[[str], bool],
) -> TextObjectRange:
    start = offset
    end = offset
    current = text[offset]

    if isWordChar(current):
        while start > 0 and isWordChar(text[start - 1]):
            start -= 1
        while end < len(text) and isWordChar(text[end]):
            end += 1
    elif isVimWhitespace(current):
        while start > 0 and isVimWhitespace(text[start - 1]):
            start -= 1
        while end < len(text) and isVimWhitespace(text[end]):
            end += 1
        return {"start": start, "end": end}
    elif isVimPunctuation(current):
        while start > 0 and isVimPunctuation(text[start - 1]):
            start -= 1
        while end < len(text) and isVimPunctuation(text[end]):
            end += 1
    else:
        return None

    if not isInner:
        if end < len(text) and isVimWhitespace(text[end]):
            while end < len(text) and isVimWhitespace(text[end]):
                end += 1
        elif start > 0 and isVimWhitespace(text[start - 1]):
            while start > 0 and isVimWhitespace(text[start - 1]):
                start -= 1

    return {"start": start, "end": end}


def findQuoteObject(text: str, offset: int, quote: str, isInner: bool) -> TextObjectRange:
    line_start = text.rfind("\n", 0, offset) + 1
    line_end = text.find("\n", offset)
    effective_end = len(text) if line_end == -1 else line_end
    line = text[line_start:effective_end]
    pos_in_line = offset - line_start
    positions = [index for index, char in enumerate(line) if char == quote]

    for index in range(0, len(positions) - 1, 2):
        quote_start = positions[index]
        quote_end = positions[index + 1]
        if quote_start <= pos_in_line <= quote_end:
            if isInner:
                return {"start": line_start + quote_start + 1, "end": line_start + quote_end}
            return {"start": line_start + quote_start, "end": line_start + quote_end + 1}
    return None


def findBracketObject(
    text: str,
    offset: int,
    open_char: str,
    close_char: str,
    isInner: bool,
) -> TextObjectRange:
    depth = 0
    start = -1
    for index in range(offset, -1, -1):
        char = text[index]
        if char == close_char and index != offset:
            depth += 1
        elif char == open_char:
            if depth == 0:
                start = index
                break
            depth -= 1
    if start == -1:
        return None

    depth = 0
    end = -1
    for index in range(start + 1, len(text)):
        char = text[index]
        if char == open_char:
            depth += 1
        elif char == close_char:
            if depth == 0:
                end = index
                break
            depth -= 1
    if end == -1:
        return None

    if isInner:
        return {"start": start + 1, "end": end}
    return {"start": start, "end": end + 1}


find_text_object = findTextObject
find_word_object = findWordObject
find_quote_object = findQuoteObject
find_bracket_object = findBracketObject