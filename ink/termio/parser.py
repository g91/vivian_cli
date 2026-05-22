"""Port of src/ink/termio/parser.ts."""
from __future__ import annotations

from typing import Any

from .tokenize import Tokenizer, createTokenizer
from .types import (
    TextStyle, defaultStyle, Grapheme, TextSegment,
    NamedColor, Color, CursorDirection,
)
from .sgr import (
    SGR_RESET, SGR_BOLD, SGR_DIM, SGR_ITALIC, SGR_UNDERLINE,
    SGR_INVERSE, SGR_STRIKETHROUGH, SGR_FG, SGR_BG,
    SGR_FG_DEFAULT, SGR_BG_DEFAULT,
    NAMED_FG, NAMED_BG, NAMED_FG_BRIGHT, NAMED_BG_BRIGHT,
)
from .esc import RIS


class Parser:
    def __init__(self) -> None:
        self._tokenizer = createTokenizer()
        self._style = defaultStyle.copy()
        self._actions: list[dict[str, Any]] = []

    def feed(self, data: str) -> list[dict[str, Any]]:
        tokens = self._tokenizer.feed(data)
        self._actions = []
        for token in tokens:
            if token.type == "text":
                self._handle_text(token.value)
            elif token.type == "sequence":
                self._handle_sequence(token.value)
        return self._actions

    def flush(self) -> list[dict[str, Any]]:
        tokens = self._tokenizer.flush()
        self._actions = []
        for token in tokens:
            if token.type == "text":
                self._handle_text(token.value)
            elif token.type == "sequence":
                self._handle_sequence(token.value)
        return self._actions

    def _handle_text(self, text: str) -> None:
        graphemes = [Grapheme(text=ch) for ch in text]
        self._actions.append({
            "type": "text",
            "graphemes": graphemes,
            "style": self._style.copy(),
        })

    def _handle_sequence(self, seq: str) -> None:
        if len(seq) < 2:
            return

        # CSI sequences
        if seq.startswith("\x1b["):
            self._handle_csi(seq[2:])
        # OSC sequences
        elif seq.startswith("\x1b]"):
            self._handle_osc(seq[2:])
        # Simple ESC
        elif len(seq) == 2:
            self._handle_esc(seq[1])

    def _handle_csi(self, params_str: str) -> None:
        if not params_str:
            return
        final = params_str[-1]
        params = params_str[:-1]

        # Parse numeric params
        nums = []
        if params:
            for p in params.split(";"):
                try:
                    nums.append(int(p))
                except ValueError:
                    nums.append(0)

        if final == "m":
            self._handle_sgr(nums)
        elif final == "A":
            self._actions.append({"type": "cursor", "direction": "up", "count": nums[0] if nums else 1})
        elif final == "B":
            self._actions.append({"type": "cursor", "direction": "down", "count": nums[0] if nums else 1})
        elif final == "C":
            self._actions.append({"type": "cursor", "direction": "right", "count": nums[0] if nums else 1})
        elif final == "D":
            self._actions.append({"type": "cursor", "direction": "left", "count": nums[0] if nums else 1})
        elif final == "H":
            self._actions.append({"type": "cursor", "direction": "home", "row": nums[0] - 1 if len(nums) > 0 else 0, "col": nums[1] - 1 if len(nums) > 1 else 0})
        elif final == "J":
            self._actions.append({"type": "erase", "mode": nums[0] if nums else 0})
        elif final == "K":
            self._actions.append({"type": "erase_line", "mode": nums[0] if nums else 0})
        elif final == "h":
            self._actions.append({"type": "mode", "set": True, "mode": nums[0] if nums else 0})
        elif final == "l":
            self._actions.append({"type": "mode", "set": False, "mode": nums[0] if nums else 0})

    def _handle_sgr(self, params: list[int]) -> None:
        if not params:
            params = [0]

        i = 0
        while i < len(params):
            p = params[i]

            if p == SGR_RESET:
                self._style = defaultStyle.copy()
            elif p == SGR_BOLD:
                self._style.bold = True
            elif p == SGR_DIM:
                self._style.dim = True
            elif p == 22:
                self._style.bold = False
                self._style.dim = False
            elif p == SGR_ITALIC:
                self._style.italic = True
            elif p == 23:
                self._style.italic = False
            elif p == SGR_UNDERLINE:
                self._style.underline = "single"
            elif p == 21:
                self._style.underline = "double"
            elif p == 24:
                self._style.underline = None
            elif p == SGR_INVERSE:
                self._style.inverse = True
            elif p == 27:
                self._style.inverse = False
            elif p == SGR_STRIKETHROUGH:
                self._style.strikethrough = True
            elif p == 29:
                self._style.strikethrough = False
            elif p == 8:
                self._style.hidden = True
            elif p == 28:
                self._style.hidden = False
            elif p in NAMED_FG.values():
                name = {v: k for k, v in NAMED_FG.items()}.get(p, "white")
                self._style.fg = {"type": "named", "name": name}
            elif p in NAMED_BG.values():
                name = {v: k for k, v in NAMED_BG.items()}.get(p, "white")
                self._style.bg = {"type": "named", "name": name}
            elif p in NAMED_FG_BRIGHT.values():
                name = {v: k for k, v in NAMED_FG_BRIGHT.items()}.get(p, "white")
                self._style.fg = {"type": "named", "name": f"bright{name.capitalize()}"}
            elif p in NAMED_BG_BRIGHT.values():
                name = {v: k for k, v in NAMED_BG_BRIGHT.items()}.get(p, "white")
                self._style.bg = {"type": "named", "name": f"bright{name.capitalize()}"}
            elif p == SGR_FG_DEFAULT:
                self._style.fg = None
            elif p == SGR_BG_DEFAULT:
                self._style.bg = None
            elif p == SGR_FG:
                if i + 1 < len(params):
                    if params[i + 1] == 5 and i + 2 < len(params):
                        self._style.fg = {"type": "indexed", "index": params[i + 2]}
                        i += 2
                    elif params[i + 1] == 2 and i + 4 < len(params):
                        self._style.fg = {"type": "rgb", "r": params[i + 2], "g": params[i + 3], "b": params[i + 4]}
                        i += 4
            elif p == SGR_BG:
                if i + 1 < len(params):
                    if params[i + 1] == 5 and i + 2 < len(params):
                        self._style.bg = {"type": "indexed", "index": params[i + 2]}
                        i += 2
                    elif params[i + 1] == 2 and i + 4 < len(params):
                        self._style.bg = {"type": "rgb", "r": params[i + 2], "g": params[i + 3], "b": params[i + 4]}
                        i += 4

            i += 1

    def _handle_osc(self, params_str: str) -> None:
        # Strip trailing BEL or ST
        params_str = params_str.rstrip("\x07").rstrip("\x1b\\")
        parts = params_str.split(";", 1)
        code = int(parts[0]) if parts else 0
        data = parts[1] if len(parts) > 1 else ""

        if code == 8:
            # OSC 8 hyperlink
            params = {}
            for p in data.split(";"):
                if "=" in p:
                    k, v = p.split("=", 1)
                    params[k] = v
            self._actions.append({
                "type": "link",
                "uri": params.get("uri", params.get("", "")),
                "id": params.get("id"),
            })
        elif code == 0 or code == 2:
            self._actions.append({"type": "title", "title": data})

    def _handle_esc(self, code: str) -> None:
        seq = f"\x1b{code}"
        if seq == RIS:
            self._style = defaultStyle.copy()
            self._actions.append({"type": "reset"})
            return
        self._actions.append({"type": "escape", "sequence": seq})
