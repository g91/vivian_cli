"""Port of src/ink/screen.py - Packed cell buffer for terminal rendering."""
from __future__ import annotations

import array
from typing import Any

# Cell width constants
class CellWidth:
    Narrow = 0
    Wide = 1
    SpacerTail = 2
    SpacerHead = 3


# --- Shared Pools ---

class CharPool:
    __slots__ = ("_strings", "_index")
    def __init__(self) -> None:
        self._strings: list[str] = [" ", ""]  # 0=empty, 1=spacer
        self._index: dict[str, int] = {" ": 0, "": 1}

    def intern(self, char: str) -> int:
        idx = self._index.get(char)
        if idx is not None:
            return idx
        idx = len(self._strings)
        self._strings.append(char)
        self._index[char] = idx
        return idx

    def get(self, idx: int) -> str:
        return self._strings[idx] if 0 <= idx < len(self._strings) else " "

    def __len__(self) -> int:
        return len(self._strings)


class HyperlinkPool:
    __slots__ = ("_links", "_index")
    def __init__(self) -> None:
        self._links: list[str | None] = [None]  # 0 = no hyperlink
        self._index: dict[str, int] = {}

    def intern(self, link: str | None) -> int:
        if link is None:
            return 0
        idx = self._index.get(link)
        if idx is not None:
            return idx
        idx = len(self._links)
        self._links.append(link)
        self._index[link] = idx
        return idx

    def get(self, idx: int) -> str | None:
        return self._links[idx] if 0 <= idx < len(self._links) else None


class StylePool:
    __slots__ = ("_styles", "_index", "_transitions", "none")

    def __init__(self) -> None:
        self._styles: list[list[dict[str, Any]]] = [[]]  # 0 = no style
        self._index: dict[str, int] = {"": 0}
        self._transitions: dict[tuple[int, int], str] = {}
        self.none = 0

    def intern(self, styles: list[dict[str, Any]]) -> int:
        key = self._styles_key(styles)
        idx = self._index.get(key)
        if idx is not None:
            return idx
        idx = len(self._styles)
        self._styles.append(styles)
        self._index[key] = idx
        return idx

    def transition(self, from_id: int, to_id: int) -> str:
        if from_id == to_id:
            return ""
        cache_key = (from_id, to_id)
        cached = self._transitions.get(cache_key)
        if cached is not None:
            return cached
        result = self._build_transition(from_id, to_id)
        self._transitions[cache_key] = result
        return result

    def _build_transition(self, from_id: int, to_id: int) -> str:
        from_styles = self._styles[from_id] if from_id < len(self._styles) else []
        to_styles = self._styles[to_id] if to_id < len(self._styles) else []
        # Build SGR reset + target styles
        if not to_styles:
            return "\x1b[0m"
        codes = ["0"]
        for s in to_styles:
            code = s.get("code", "")
            if code:
                codes.append(code.replace("\x1b[", "").rstrip("m"))
        return f"\x1b[{';'.join(codes)}m"

    def withInverse(self, style_id: int) -> int:
        styles = list(self._styles[style_id]) if style_id < len(self._styles) else []
        styles.append({"type": "ansi", "code": "\x1b[7m", "endCode": "\x1b[27m"})
        return self.intern(styles)

    def withCurrentMatch(self, style_id: int) -> int:
        styles = list(self._styles[style_id]) if style_id < len(self._styles) else []
        styles.extend([
            {"type": "ansi", "code": "\x1b[33m", "endCode": "\x1b[39m"},
            {"type": "ansi", "code": "\x1b[1m", "endCode": "\x1b[22m"},
            {"type": "ansi", "code": "\x1b[4m", "endCode": "\x1b[24m"},
        ])
        return self.intern(styles)

    @staticmethod
    def _styles_key(styles: list[dict[str, Any]]) -> str:
        return ";".join(s.get("code", "") for s in styles)


# --- Screen ---

STYLE_SHIFT = 17
HYPERLINK_SHIFT = 2
HYPERLINK_MASK = 0x7FFF
WIDTH_MASK = 3


class Screen:
    __slots__ = (
        "width", "height", "cells", "charPool", "hyperlinkPool",
        "emptyStyleId", "damage", "noSelect", "softWrap",
    )

    def __init__(
        self, width: int, height: int,
        charPool: CharPool, hyperlinkPool: HyperlinkPool,
    ) -> None:
        self.width = width
        self.height = height
        size = max(1, width * height * 2)
        self.cells = array.array("i", [0]) * size
        self.charPool = charPool
        self.hyperlinkPool = hyperlinkPool
        self.emptyStyleId = 0
        self.damage: dict[str, int] | None = None
        self.noSelect = array.array("B", [0]) * max(1, width * height)
        self.softWrap = array.array("i", [0]) * max(1, height)


def createScreen(
    width: int, height: int,
    stylePool: StylePool, charPool: CharPool, hyperlinkPool: HyperlinkPool,
) -> Screen:
    return Screen(width, height, charPool, hyperlinkPool)


def resetScreen(screen: Screen, width: int, height: int) -> None:
    screen.width = width
    screen.height = height
    size = max(1, width * height * 2)
    if len(screen.cells) != size:
        screen.cells = array.array("i", [0]) * size
    else:
        for i in range(size):
            screen.cells[i] = 0
    ns_size = max(1, width * height)
    if len(screen.noSelect) != ns_size:
        screen.noSelect = array.array("B", [0]) * ns_size
    else:
        for i in range(ns_size):
            screen.noSelect[i] = 0
    if len(screen.softWrap) != max(1, height):
        screen.softWrap = array.array("i", [0]) * max(1, height)
    else:
        for i in range(max(1, height)):
            screen.softWrap[i] = 0
    screen.damage = None


def _packWord1(styleId: int, hyperlinkId: int, width: int) -> int:
    return (styleId << STYLE_SHIFT) | ((hyperlinkId & HYPERLINK_MASK) << HYPERLINK_SHIFT) | (width & WIDTH_MASK)


def cellAtIndex(screen: Screen, index: int) -> dict[str, Any]:
    ci = index * 2
    char_id = screen.cells[ci]
    word1 = screen.cells[ci + 1] if ci + 1 < len(screen.cells) else 0
    style_id = word1 >> STYLE_SHIFT
    hyperlink_id = (word1 >> HYPERLINK_SHIFT) & HYPERLINK_MASK
    width = word1 & WIDTH_MASK
    return {
        "char": screen.charPool.get(char_id),
        "styleId": style_id,
        "width": width,
        "hyperlink": screen.hyperlinkPool.get(hyperlink_id),
    }


def cellAt(screen: Screen, x: int, y: int) -> dict[str, Any] | None:
    if x < 0 or x >= screen.width or y < 0 or y >= screen.height:
        return None
    return cellAtIndex(screen, y * screen.width + x)


def setCellAt(screen: Screen, x: int, y: int, cell: dict[str, Any]) -> None:
    if x < 0 or x >= screen.width or y < 0 or y >= screen.height:
        return
    idx = (y * screen.width + x) * 2
    char_id = screen.charPool.intern(cell.get("char", " "))
    hyperlink_id = screen.hyperlinkPool.intern(cell.get("hyperlink"))
    style_id = cell.get("styleId", 0)
    width = cell.get("width", CellWidth.Narrow)
    screen.cells[idx] = char_id
    screen.cells[idx + 1] = _packWord1(style_id, hyperlink_id, width)

    # Set spacer for wide chars
    if width == CellWidth.Wide and x + 1 < screen.width:
        spacer_idx = (y * screen.width + x + 1) * 2
        screen.cells[spacer_idx] = 1  # spacer char
        screen.cells[spacer_idx + 1] = _packWord1(style_id, hyperlink_id, CellWidth.SpacerTail)


def setCellStyleId(screen: Screen, x: int, y: int, styleId: int) -> None:
    if x < 0 or x >= screen.width or y < 0 or y >= screen.height:
        return
    idx = (y * screen.width + x) * 2 + 1
    word1 = screen.cells[idx]
    hyperlink_id = (word1 >> HYPERLINK_SHIFT) & HYPERLINK_MASK
    width = word1 & WIDTH_MASK
    screen.cells[idx] = _packWord1(styleId, hyperlink_id, width)


def isEmptyCellAt(screen: Screen, x: int, y: int) -> bool:
    if x < 0 or x >= screen.width or y < 0 or y >= screen.height:
        return True
    idx = (y * screen.width + x) * 2
    return screen.cells[idx] == 0 and screen.cells[idx + 1] == 0


def isCellEmpty(screen: Screen, cell: dict[str, Any]) -> bool:
    return cell.get("char", " ") == " " and cell.get("styleId", 0) == 0


def charInCellAt(screen: Screen, x: int, y: int) -> str | None:
    cell = cellAt(screen, x, y)
    return cell["char"] if cell else None


def blitRegion(
    dst: Screen, src: Screen,
    regionX: int, regionY: int, maxX: int, maxY: int,
) -> None:
    x1 = max(0, regionX)
    y1 = max(0, regionY)
    x2 = min(dst.width, maxX)
    y2 = min(dst.height, maxY)
    for y in range(y1, y2):
        src_row = y * src.width
        dst_row = y * dst.width
        for x in range(x1, x2):
            si = (src_row + x) * 2
            di = (dst_row + x) * 2
            dst.cells[di] = src.cells[si]
            dst.cells[di + 1] = src.cells[si + 1]


def clearRegion(
    screen: Screen,
    regionX: int, regionY: int,
    regionWidth: int, regionHeight: int,
) -> None:
    x1 = max(0, regionX)
    y1 = max(0, regionY)
    x2 = min(screen.width, regionX + regionWidth)
    y2 = min(screen.height, regionY + regionHeight)
    for y in range(y1, y2):
        row = y * screen.width
        for x in range(x1, x2):
            idx = (row + x) * 2
            screen.cells[idx] = 0
            screen.cells[idx + 1] = 0


def shiftRows(screen: Screen, top: int, bottom: int, n: int) -> None:
    if n == 0:
        return
    row_size = screen.width * 2
    if n > 0:
        # Shift up
        for y in range(top, bottom - n + 1):
            src = y + n
            dst_start = y * screen.width * 2
            src_start = src * screen.width * 2
            screen.cells[dst_start:dst_start + row_size] = screen.cells[src_start:src_start + row_size]
        # Clear vacated rows
        for y in range(bottom - n + 1, bottom + 1):
            start = y * screen.width * 2
            for i in range(start, start + row_size):
                screen.cells[i] = 0
    else:
        # Shift down
        n = -n
        for y in range(bottom, top + n - 1, -1):
            src = y - n
            dst_start = y * screen.width * 2
            src_start = src * screen.width * 2
            screen.cells[dst_start:dst_start + row_size] = screen.cells[src_start:src_start + row_size]
        for y in range(top, top + n):
            start = y * screen.width * 2
            for i in range(start, start + row_size):
                screen.cells[i] = 0


def markNoSelectRegion(screen: Screen, x: int, y: int, width: int, height: int) -> None:
    for row in range(y, min(y + height, screen.height)):
        row_start = row * screen.width
        for col in range(x, min(x + width, screen.width)):
            screen.noSelect[row_start + col] = 1


def extractHyperlinkFromStyles(styles: list[dict[str, Any]]) -> str | None:
    for s in styles:
        code = s.get("code", "")
        if code.startswith("\x1b]8;"):
            parts = code.split(";")
            for p in parts:
                if p.startswith("uri="):
                    return p[4:]
    return None


def filterOutHyperlinkStyles(styles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [s for s in styles if not s.get("code", "").startswith("\x1b]8")]


def diff(prev: Screen, next: Screen) -> list[tuple[dict[str, int], dict[str, Any] | None, dict[str, Any] | None]]:
    result: list[tuple[dict[str, int], dict[str, Any] | None, dict[str, Any] | None]] = []
    h = min(prev.height, next.height)
    w = min(prev.width, next.width)
    for y in range(h):
        for x in range(w):
            pi = (y * prev.width + x) * 2
            ni = (y * next.width + x) * 2
            if prev.cells[pi] != next.cells[ni] or prev.cells[pi + 1] != next.cells[ni + 1]:
                result.append((
                    {"x": x, "y": y},
                    cellAtIndex(prev, y * prev.width + x),
                    cellAtIndex(next, y * next.width + x),
                ))
    return result


create_screen = createScreen
reset_screen = resetScreen
cell_at = cellAt
cell_at_index = cellAtIndex
set_cell_at = setCellAt
set_cell_style_id = setCellStyleId
is_empty_cell_at = isEmptyCellAt
is_cell_empty = isCellEmpty
char_in_cell_at = charInCellAt
blit_region = blitRegion
clear_region = clearRegion
shift_rows = shiftRows
mark_no_select_region = markNoSelectRegion
extract_hyperlink_from_styles = extractHyperlinkFromStyles
filter_out_hyperlink_styles = filterOutHyperlinkStyles
