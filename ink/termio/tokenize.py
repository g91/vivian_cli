"""Port of src/ink/termio/tokenize.ts."""
from __future__ import annotations

from typing import Any

from .ansi import BEL, ESC, ST


class Token:
    __slots__ = ("type", "value")
    def __init__(self, type: str, value: str) -> None:
        self.type = type
        self.value = value


class Tokenizer:
    def __init__(self, x10Mouse: bool = False) -> None:
        self._buffer = ""
        self._x10_mouse = x10Mouse

    def feed(self, data: str) -> list[Token]:
        self._buffer += data
        tokens: list[Token] = []
        i = 0
        buf = self._buffer

        while i < len(buf):
            if buf[i] == ESC:
                end = self._find_sequence_end(buf, i)
                if end == -1:
                    break
                tokens.append(Token("sequence", buf[i:end]))
                i = end
            else:
                j = i
                while j < len(buf) and buf[j] != ESC:
                    j += 1
                if j > i:
                    tokens.append(Token("text", buf[i:j]))
                i = j

        self._buffer = buf[i:]
        return tokens

    def flush(self) -> list[Token]:
        tokens = self.feed("")
        remaining = self._buffer
        self._buffer = ""
        if remaining:
            tokens.append(Token("text", remaining))
        return tokens

    def buffer(self) -> str:
        return self._buffer

    def _find_sequence_end(self, buf: str, start: int) -> int:
        i = start + 1
        if i >= len(buf):
            return -1

        c = buf[i]

        # ESC ] (OSC) - terminated by BEL or ST
        if c == "]":
            i += 1
            while i < len(buf):
                if buf[i] == BEL:
                    return i + 1
                if buf[i:i+2] == ST:
                    return i + 2
                i += 1
            return -1

        # ESC P (DCS), ESC ^ (PM), ESC _ (APC) - terminated by ST
        if c in "P^_":
            i += 1
            while i < len(buf):
                if buf[i:i+2] == ST:
                    return i + 2
                i += 1
            return -1

        # CSI sequences: ESC [ ... final byte
        if c == "[":
            i += 1
            while i < len(buf):
                b = ord(buf[i])
                if 0x40 <= b <= 0x7E:
                    return i + 1
                if b < 0x20 or b > 0x7E:
                    break
                i += 1
            return -1

        # Simple ESC sequences
        return i + 1


def createTokenizer(x10Mouse: bool = False) -> Tokenizer:
    return Tokenizer(x10Mouse)


create_tokenizer = createTokenizer
