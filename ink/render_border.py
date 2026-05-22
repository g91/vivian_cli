"""Port of src/ink/render-border.ts."""
from __future__ import annotations

from typing import Any

from .dom import DOMNode
from .output import Output
from .stringWidth import stringWidth
from .colorize import applyColor
from .styles import Color

CUSTOM_BORDER_STYLES = {
    "dashed": {
        "top": "\u254c", "left": "\u254e", "right": "\u254e", "bottom": "\u254c",
        "topLeft": " ", "topRight": " ", "bottomLeft": " ", "bottomRight": " ",
    },
}

DEFAULT_BOX = {
    "top": "\u2500", "bottom": "\u2500", "left": "\u2502", "right": "\u2502",
    "topLeft": "\u250c", "topRight": "\u2510", "bottomLeft": "\u2514", "bottomRight": "\u2518",
}


def _getBox(style: Any) -> dict[str, str]:
    if isinstance(style, str):
        return CUSTOM_BORDER_STYLES.get(style) or DEFAULT_BOX
    if isinstance(style, dict):
        return style
    return DEFAULT_BOX


def renderBorder(x: int, y: int, node: DOMNode, output: Output) -> None:
    style = node.style
    if not style.get("borderStyle"):
        return

    yoga = node.yogaNode
    if not yoga:
        return

    width = int(yoga.getComputedWidth())
    height = int(yoga.getComputedHeight())
    box = _getBox(style["borderStyle"])

    topColor = style.get("borderTopColor") or style.get("borderColor")
    bottomColor = style.get("borderBottomColor") or style.get("borderColor")
    leftColor = style.get("borderLeftColor") or style.get("borderColor")
    rightColor = style.get("borderRightColor") or style.get("borderColor")

    showTop = style.get("borderTop", True)
    showBottom = style.get("borderBottom", True)
    showLeft = style.get("borderLeft", True)
    showRight = style.get("borderRight", True)

    contentWidth = max(0, width - (1 if showLeft else 0) - (1 if showRight else 0))

    if showTop:
        topLine = (box["topLeft"] if showLeft else "") + box["top"] * contentWidth + (box["topRight"] if showRight else "")
        output.write(x, y, applyColor(topLine, topColor))

    if showBottom:
        bottomLine = (box["bottomLeft"] if showLeft else "") + box["bottom"] * contentWidth + (box["bottomRight"] if showRight else "")
        output.write(x, y + height - 1, applyColor(bottomLine, bottomColor))

    vertHeight = height - (1 if showTop else 0) - (1 if showBottom else 0)
    vertHeight = max(0, vertHeight)
    offsetY = y + (1 if showTop else 0)

    if showLeft:
        leftStr = applyColor(box["left"], leftColor)
        for row in range(vertHeight):
            output.write(x, offsetY + row, leftStr)

    if showRight:
        rightStr = applyColor(box["right"], rightColor)
        for row in range(vertHeight):
            output.write(x + width - 1, offsetY + row, rightStr)
