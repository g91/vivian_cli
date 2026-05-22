"""Port of src/ink/selection.ts."""
from __future__ import annotations

from typing import Any

from .screen import Screen, StylePool, cellAtIndex, setCellStyleId, CellWidth

SelectionState = dict[str, Any]


def createSelectionState() -> SelectionState:
    return {
        "anchor": None,
        "focus": None,
        "isDragging": False,
        "anchorSpan": None,
        "scrolledOffAbove": [],
        "scrolledOffBelow": [],
        "scrolledOffAboveSW": [],
        "scrolledOffBelowSW": [],
        "lastPressHadAlt": False,
    }


def startSelection(s: SelectionState, col: int, row: int) -> None:
    s["anchor"] = {"col": col, "row": row}
    s["focus"] = {"col": col, "row": row}
    s["isDragging"] = True
    s["anchorSpan"] = None


def updateSelection(s: SelectionState, col: int, row: int) -> None:
    s["focus"] = {"col": col, "row": row}


def finishSelection(s: SelectionState) -> None:
    s["isDragging"] = False


def clearSelection(s: SelectionState) -> None:
    s["anchor"] = None
    s["focus"] = None
    s["isDragging"] = False
    s["anchorSpan"] = None
    s["scrolledOffAbove"] = []
    s["scrolledOffBelow"] = []
    s["scrolledOffAboveSW"] = []
    s["scrolledOffBelowSW"] = []


def hasSelection(s: SelectionState) -> bool:
    return s["anchor"] is not None and s["focus"] is not None


def selectionBounds(s: SelectionState) -> dict[str, dict[str, int]] | None:
    a = s["anchor"]
    f = s["focus"]
    if not a or not f:
        return None
    if a["row"] < f["row"] or (a["row"] == f["row"] and a["col"] <= f["col"]):
        return {"start": a, "end": f}
    return {"start": f, "end": a}


def isCellSelected(s: SelectionState, col: int, row: int) -> bool:
    bounds = selectionBounds(s)
    if not bounds:
        return False
    start = bounds["start"]
    end = bounds["end"]
    if row < start["row"] or row > end["row"]:
        return False
    if row == start["row"] and col < start["col"]:
        return False
    if row == end["row"] and col > end["col"]:
        return False
    return True


def getSelectedText(s: SelectionState, screen: Screen) -> str:
    bounds = selectionBounds(s)
    if not bounds:
        return ""
    start = bounds["start"]
    end = bounds["end"]
    lines: list[str] = []
    for row in range(start["row"], end["row"] + 1):
        colStart = start["col"] if row == start["row"] else 0
        colEnd = end["col"] if row == end["row"] else screen.width - 1
        line = ""
        for col in range(colStart, colEnd + 1):
            cell = cellAtIndex(screen, row * screen.width + col)
            if cell["width"] in (CellWidth.SpacerTail, CellWidth.SpacerHead):
                continue
            if screen.noSelect[row * screen.width + col] == 1:
                continue
            line += cell["char"]
        lines.append(line.rstrip())
    return "\n".join(lines)


def applySelectionOverlay(screen: Screen, selection: SelectionState, stylePool: StylePool) -> None:
    bounds = selectionBounds(selection)
    if not bounds:
        return
    start = bounds["start"]
    end = bounds["end"]
    for row in range(start["row"], end["row"] + 1):
        colStart = start["col"] if row == start["row"] else 0
        colEnd = end["col"] if row == end["row"] else screen.width - 1
        for col in range(colStart, colEnd + 1):
            cell = cellAtIndex(screen, row * screen.width + col)
            if cell["width"] in (CellWidth.SpacerTail, CellWidth.SpacerHead):
                continue
            setCellStyleId(screen, col, row, stylePool.withInverse(cell["styleId"]))


def shiftSelection(s: SelectionState, dRow: int, minRow: int, maxRow: int, width: int) -> None:
    for key in ("anchor", "focus"):
        pt = s.get(key)
        if pt:
            pt["row"] = max(minRow, min(maxRow, pt["row"] + dRow))


def shiftAnchor(s: SelectionState, dRow: int, minRow: int, maxRow: int) -> None:
    a = s.get("anchor")
    if a:
        a["row"] = max(minRow, min(maxRow, a["row"] + dRow))


def shiftSelectionForFollow(s: SelectionState, dRow: int, minRow: int, maxRow: int) -> bool:
    a = s.get("anchor")
    f = s.get("focus")
    if not a or not f:
        return False
    newARow = a["row"] + dRow
    newFRow = f["row"] + dRow
    if newARow < minRow and newFRow < minRow:
        clearSelection(s)
        return True
    a["row"] = max(minRow, min(maxRow, newARow))
    f["row"] = max(minRow, min(maxRow, newFRow))
    return False


def captureScrolledRows(s: SelectionState, screen: Screen, firstRow: int, lastRow: int, side: str) -> None:
    lines: list[str] = []
    for row in range(firstRow, lastRow + 1):
        line = ""
        for col in range(screen.width):
            cell = cellAtIndex(screen, row * screen.width + col)
            if cell["width"] in (CellWidth.SpacerTail, CellWidth.SpacerHead):
                continue
            line += cell["char"]
        lines.append(line.rstrip())
    if side == "above":
        s["scrolledOffAbove"].extend(lines)
    else:
        s["scrolledOffBelow"].extend(lines)
