"""Port of src/ink/render-to-screen.ts."""
from __future__ import annotations

from typing import Any

from .dom import createNode, DOMElement
from .focus import FocusManager
from .output import Output
from .screen import (
    Screen, StylePool, CharPool, HyperlinkPool,
    createScreen, cellAtIndex, setCellStyleId, CellWidth,
)
from .render_node_to_output import renderNodeToOutput, resetLayoutShifted

MatchPosition = dict[str, int]

_root: DOMElement | None = None
_stylePool: StylePool | None = None
_charPool: CharPool | None = None
_hyperlinkPool: HyperlinkPool | None = None
_output: Output | None = None


def renderToScreen(el: Any, width: int) -> dict[str, Any]:
    global _root, _stylePool, _charPool, _hyperlinkPool, _output

    if not _root:
        _root = createNode("ink-root")
        _root.focusManager = FocusManager(lambda n, e: False)
        _stylePool = StylePool()
        _charPool = CharPool()
        _hyperlinkPool = HyperlinkPool()

    # Build tree from element
    _root.childNodes.clear()
    if hasattr(el, "build"):
        child = el.build()
        if child:
            _root.childNodes.append(child)
            child.parentNode = _root

    _root.yogaNode.setWidth(width)
    _root.yogaNode.calculateLayout(width)
    height = max(1, int(_root.yogaNode.getComputedHeight()))

    screen = createScreen(width, height, _stylePool, _charPool, _hyperlinkPool)
    if _output:
        _output.reset(width, height, screen)
    else:
        _output = Output(width, height, _stylePool, screen)

    resetLayoutShifted()
    renderNodeToOutput(_root, _output, {"prevScreen": None})
    rendered = _output.get()

    return {"screen": rendered, "height": height}


def scanPositions(screen: Screen, query: str) -> list[MatchPosition]:
    lq = query.lower()
    if not lq:
        return []
    qlen = len(lq)
    w = screen.width
    h = screen.height
    noSelect = screen.noSelect
    positions: list[MatchPosition] = []

    for row in range(h):
        rowOff = row * w
        text = ""
        colOf: list[int] = []
        codeUnitToCell: list[int] = []

        for col in range(w):
            idx = rowOff + col
            cell = cellAtIndex(screen, idx)
            if cell["width"] in (CellWidth.SpacerTail, CellWidth.SpacerHead) or noSelect[idx] == 1:
                continue
            lc = cell["char"].lower()
            cellIdx = len(colOf)
            for _ in range(len(lc)):
                codeUnitToCell.append(cellIdx)
            text += lc
            colOf.append(col)

        pos = text.find(lq)
        while pos >= 0:
            startCi = codeUnitToCell[pos] if pos < len(codeUnitToCell) else 0
            endCi = codeUnitToCell[pos + qlen - 1] if pos + qlen - 1 < len(codeUnitToCell) else startCi
            col = colOf[startCi] if startCi < len(colOf) else 0
            endCol = (colOf[endCi] if endCi < len(colOf) else col) + 1
            positions.append({"row": row, "col": col, "len": endCol - col})
            pos = text.find(lq, pos + qlen)

    return positions


def applyPositionedHighlight(
    screen: Screen, stylePool: StylePool,
    positions: list[MatchPosition], rowOffset: int, currentIdx: int,
) -> bool:
    if currentIdx < 0 or currentIdx >= len(positions):
        return False
    p = positions[currentIdx]
    row = p["row"] + rowOffset
    if row < 0 or row >= screen.height:
        return False

    def transform(styleId: int) -> int:
        return stylePool.withCurrentMatch(styleId)

    rowOff = row * screen.width
    for col in range(p["col"], p["col"] + p["len"]):
        if col < 0 or col >= screen.width:
            continue
        cell = cellAtIndex(screen, rowOff + col)
        setCellStyleId(screen, col, row, transform(cell["styleId"]))
    return True
