"""Port of src/ink/log-update.ts - Screen diff engine."""
from __future__ import annotations

from typing import Any

from .frame import Frame, Diff, FlickerReason
from .screen import Screen, StylePool, cellAtIndex, CellWidth
from .clearTerminal import getClearTerminalSequence
from .termio.csi import CURSOR_HOME, ERASE_SCREEN, cursorMove, cursorTo, eraseLines
from .termio.dec import HIDE_CURSOR, SHOW_CURSOR
from .termio.osc import link


class LogUpdate:
    __slots__ = ("options", "state")

    def __init__(self, isTTY: bool, stylePool: StylePool) -> None:
        self.options = {"isTTY": isTTY, "stylePool": stylePool}
        self.state = {"previousOutput": ""}

    def reset(self) -> None:
        self.state["previousOutput"] = ""

    def renderPreviousOutput_DEPRECATED(self, prevFrame: Frame) -> Diff:
        if not self.options["isTTY"]:
            return self._renderFullFrame(prevFrame)
        return self._getRenderOpsForDone(prevFrame)

    def _renderFullFrame(self, frame: Frame) -> Diff:
        screen = frame.screen
        lines: list[str] = []
        for y in range(screen.height):
            line = ""
            for x in range(screen.width):
                cell = cellAtIndex(screen, y * screen.width + x)
                if cell["width"] == CellWidth.SpacerTail:
                    continue
                line += cell["char"]
            lines.append(line.rstrip())
        if not lines:
            return []
        return [{"type": "stdout", "content": "\n".join(lines)}]

    def _getRenderOpsForDone(self, prev: Frame) -> Diff:
        self.state["previousOutput"] = ""
        if not prev.cursor.visible:
            return [{"type": "cursorShow"}]
        return []

    def render(self, prev: Frame, next: Frame, altScreen: bool = False, decstbmSafe: bool = True) -> Diff:
        if not self.options["isTTY"]:
            return self._renderFullFrame(next)

        stylePool = self.options["stylePool"]

        if (next.viewport.height < prev.viewport.height or
            (prev.viewport.width != 0 and next.viewport.width != prev.viewport.width)):
            return self._fullResetSequence(next, "resize", stylePool)

        cursorAtBottom = prev.cursor.y >= prev.screen.height
        isGrowing = next.screen.height > prev.screen.height
        prevHadScrollback = cursorAtBottom and prev.screen.height >= prev.viewport.height
        isShrinking = next.screen.height < prev.screen.height
        nextFitsViewport = next.screen.height <= prev.viewport.height

        if prevHadScrollback and nextFitsViewport and isShrinking:
            return self._fullResetSequence(next, "offscreen", stylePool)

        if prev.screen.height >= prev.viewport.height and prev.screen.height > 0 and cursorAtBottom and not isGrowing:
            viewportY = prev.screen.height - prev.viewport.height + (1 if prevHadScrollback else 0)
            if viewportY > 0:
                return self._fullResetSequence(next, "offscreen", stylePool)

        diff: Diff = []
        h = min(prev.screen.height, next.screen.height)
        w = min(prev.screen.width, next.screen.width)

        currentStyleId = stylePool.none
        currentHyperlink = None

        for y in range(h):
            for x in range(w):
                pi = (y * prev.screen.width + x) * 2
                ni = (y * next.screen.width + x) * 2
                if prev.screen.cells[pi] != next.screen.cells[ni] or prev.screen.cells[pi + 1] != next.screen.cells[ni + 1]:
                    cell = cellAtIndex(next.screen, y * next.screen.width + x)
                    if cell["width"] == CellWidth.SpacerTail:
                        continue

                    targetStyleId = cell["styleId"]
                    if targetStyleId != currentStyleId:
                        s = stylePool.transition(currentStyleId, targetStyleId)
                        if s:
                            diff.append({"type": "styleStr", "str": s})
                        currentStyleId = targetStyleId

                    targetHyperlink = cell.get("hyperlink")
                    if targetHyperlink != currentHyperlink:
                        diff.append({"type": "hyperlink", "uri": targetHyperlink or ""})
                        currentHyperlink = targetHyperlink

                    diff.append({"type": "stdout", "content": cell["char"]})

        if currentStyleId != stylePool.none:
            s = stylePool.transition(currentStyleId, stylePool.none)
            if s:
                diff.append({"type": "styleStr", "str": s})

        return diff

    def _fullResetSequence(self, frame: Frame, reason: FlickerReason, stylePool: StylePool) -> Diff:
        return [{"type": "clearTerminal", "reason": reason}]
