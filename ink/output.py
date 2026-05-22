"""Port of src/ink/output.ts - Collects write/blit/clear/clip operations from the render tree."""
from __future__ import annotations

from typing import Any

from .bidi import reorderBidi
from .screen import (
    Screen, StylePool, CharPool, HyperlinkPool,
    createScreen, resetScreen, setCellAt, CellWidth,
    extractHyperlinkFromStyles, filterOutHyperlinkStyles,
    blitRegion, clearRegion, shiftRows, markNoSelectRegion,
)
from .stringWidth import stringWidth
from .tabstops import expandTabs
from .wrap_text import wrapText
from .line_width_cache import lineWidth
from .measure_text import measureText
from .layout.geometry import Rectangle

ClusteredChar = dict[str, Any]
Operation = dict[str, Any]
Clip = dict[str, Any]


class Output:
    __slots__ = ("width", "height", "stylePool", "screen", "operations", "charCache")

    def __init__(self, width: int, height: int, stylePool: StylePool, screen: Screen) -> None:
        self.width = width
        self.height = height
        self.stylePool = stylePool
        self.screen = screen
        self.operations: list[Operation] = []
        self.charCache: dict[str, list[ClusteredChar]] = {}
        resetScreen(screen, width, height)

    def reset(self, width: int, height: int, screen: Screen) -> None:
        self.width = width
        self.height = height
        self.screen = screen
        self.operations.clear()
        resetScreen(screen, width, height)
        if len(self.charCache) > 16384:
            self.charCache.clear()

    def blit(self, src: Screen, x: int, y: int, width: int, height: int) -> None:
        self.operations.append({"type": "blit", "src": src, "x": x, "y": y, "width": width, "height": height})

    def shift(self, top: int, bottom: int, n: int) -> None:
        self.operations.append({"type": "shift", "top": top, "bottom": bottom, "n": n})

    def clear(self, region: Rectangle, fromAbsolute: bool = False) -> None:
        self.operations.append({"type": "clear", "region": region, "fromAbsolute": fromAbsolute})

    def noSelect(self, region: Rectangle) -> None:
        self.operations.append({"type": "noSelect", "region": region})

    def write(self, x: int, y: int, text: str, softWrap: list[bool] | None = None) -> None:
        if not text:
            return
        self.operations.append({"type": "write", "x": x, "y": y, "text": text, "softWrap": softWrap})

    def clip(self, clip: Clip) -> None:
        self.operations.append({"type": "clip", "clip": clip})

    def unclip(self) -> None:
        self.operations.append({"type": "unclip"})

    def get(self) -> Screen:
        screen = self.screen
        screenWidth = self.width
        screenHeight = self.height

        absoluteClears: list[Rectangle] = []
        for op in self.operations:
            if op["type"] == "clear":
                r = op["region"]
                clearRegion(screen, r.x, r.y, r.width, r.height)
                if op.get("fromAbsolute"):
                    absoluteClears.append(r)

        clips: list[Clip] = []

        for op in self.operations:
            t = op["type"]
            if t == "write":
                self._apply_write(screen, op, screenWidth, screenHeight, clips)
            elif t == "blit":
                blitRegion(screen, op["src"], op["x"], op["y"],
                           op["x"] + op["width"], op["y"] + op["height"])
            elif t == "shift":
                shiftRows(screen, op["top"], op["bottom"], op["n"])
            elif t == "clip":
                clips.append(op["clip"])
            elif t == "unclip":
                if clips:
                    clips.pop()
            elif t == "noSelect":
                r = op["region"]
                markNoSelectRegion(screen, r.x, r.y, r.width, r.height)

        return screen

    def _apply_write(self, screen: Screen, op: Operation, sw: int, sh: int, clips: list[Clip]) -> None:
        text = op["text"]
        x = op["x"]
        y = op["y"]
        softWrap = op.get("softWrap")

        lines = text.split("\n")
        for li, line in enumerate(lines):
            if y + li >= sh:
                break
            end_x = self._writeLineToScreen(screen, line, x, y + li, sw)
            if softWrap and li < len(softWrap):
                screen.softWrap[y + li] = 1 if softWrap[li] else 0

    def _writeLineToScreen(self, screen: Screen, line: str, x: int, y: int, screenWidth: int) -> int:
        if y < 0 or y >= screen.height:
            return x

        characters = self.charCache.get(line)
        if not characters:
            characters = self._tokenizeAndCluster(line)
            self.charCache[line] = characters

        offsetX = x
        for char in characters:
            if offsetX >= screenWidth:
                break
            cp = ord(char.get("value", " ")[0]) if char.get("value") else 0
            if cp <= 0x1F:
                continue
            w = char.get("width", 1)
            if w == 0:
                continue
            setCellAt(screen, offsetX, y, {
                "char": char.get("value", " "),
                "styleId": char.get("styleId", 0),
                "width": CellWidth.Wide if w == 2 else CellWidth.Narrow,
                "hyperlink": char.get("hyperlink"),
            })
            offsetX += w
        return offsetX

    def _tokenizeAndCluster(self, line: str) -> list[ClusteredChar]:
        result: list[ClusteredChar] = []
        for ch in line:
            w = stringWidth(ch)
            result.append({
                "value": ch,
                "width": w,
                "styleId": 0,
                "hyperlink": None,
            })
        return reorderBidi(result)
