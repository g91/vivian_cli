"""Port of src/ink/render-node-to-output.ts."""
from __future__ import annotations

from typing import Any

from .dom import DOMElement
from .output import Output
from .screen import Screen
from .node_cache import getCachedLayout, setCachedLayout, deleteCachedLayout, addPendingClear
from .layout.geometry import Rectangle
from .colorize import applyColor
from .styles import Color

_layoutShifted = False
_scrollHint: dict[str, int] | None = None
_scrollDrainNode: DOMElement | None = None


def resetLayoutShifted() -> None:
    global _layoutShifted
    _layoutShifted = False


def didLayoutShift() -> bool:
    return _layoutShifted


def resetScrollHint() -> None:
    global _scrollHint
    _scrollHint = None


def getScrollHint() -> dict[str, int] | None:
    return _scrollHint


def resetScrollDrainNode() -> None:
    global _scrollDrainNode
    _scrollDrainNode = None


def getScrollDrainNode() -> DOMElement | None:
    return _scrollDrainNode


def renderNodeToOutput(
    node: DOMElement,
    output: Output,
    options: dict[str, Any] | None = None,
) -> None:
    if options is None:
        options = {}

    offsetX = options.get("offsetX", 0)
    offsetY = options.get("offsetY", 0)
    prevScreen = options.get("prevScreen")
    inheritedBackgroundColor = options.get("inheritedBackgroundColor")

    yoga = node.yogaNode
    if not yoga:
        return

    x = int(yoga.getComputedLeft()) + offsetX
    y = int(yoga.getComputedTop()) + offsetY
    w = int(yoga.getComputedWidth())
    h = int(yoga.getComputedHeight())

    if w <= 0 or h <= 0:
        return

    # Cache layout
    cached = getCachedLayout(node)
    newLayout = {"x": x, "y": y, "width": w, "height": h, "top": int(yoga.getComputedTop())}
    if not cached or cached != newLayout:
        setCachedLayout(node, newLayout)

    # Render background
    bg = node.style.get("backgroundColor") or inheritedBackgroundColor
    if bg:
        for row in range(y, y + h):
            output.write(x, row, " " * w)

    # Render border
    if node.style.get("borderStyle"):
        from .render_border import renderBorder
        renderBorder(x, y, node, output)

    # Render children
    scrollTop = node.scrollTop or 0
    for child in node.childNodes:
        if child.nodeName == "#text":
            text = child.nodeValue
            if text:
                output.write(x, y, text)
        elif child.nodeName in ("ink-text", "ink-virtual-text", "ink-link", "ink-box", "ink-root", "ink-raw-ansi"):
            renderNodeToOutput(child, output, {
                "offsetX": x,
                "offsetY": y - scrollTop,
                "prevScreen": prevScreen,
                "inheritedBackgroundColor": bg or inheritedBackgroundColor,
            })
