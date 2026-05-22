"""Port of src/ink/searchHighlight.ts."""
from __future__ import annotations

from .screen import Screen, StylePool, cellAtIndex, setCellStyleId, CellWidth


def applySearchHighlight(screen: Screen, query: str, stylePool: StylePool) -> bool:
    if not query:
        return False

    lq = query.lower()
    qlen = len(lq)
    w = screen.width
    h = screen.height
    noSelect = screen.noSelect

    applied = False
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
            applied = True
            startCi = codeUnitToCell[pos] if pos < len(codeUnitToCell) else 0
            endCi = codeUnitToCell[pos + qlen - 1] if pos + qlen - 1 < len(codeUnitToCell) else startCi
            for ci in range(startCi, endCi + 1):
                if ci < len(colOf):
                    col = colOf[ci]
                    cell = cellAtIndex(screen, rowOff + col)
                    setCellStyleId(screen, col, row, stylePool.withInverse(cell["styleId"]))
            pos = text.find(lq, pos + qlen)

    return applied
