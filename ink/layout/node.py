"""Port of src/ink/layout/node.py - Yoga layout node wrapper."""
from __future__ import annotations

from typing import Any, Callable

LayoutMeasureMode = Any  # 0=Undefined, 1=Exactly, 2=AtMost
LayoutEdge = Any  # 0=Top, 1=Bottom, 2=Left, 3=Right
LayoutDisplay = Any  # 0=Flex, 1=None


class LayoutNode:
    """Minimal Yoga-like layout node for Python. In production, this would
    wrap a native Yoga implementation. For the Python port, we provide a
    simplified layout model."""

    __slots__ = (
        "_children", "_parent", "_style", "_layout",
        "_measureFunc", "_dirty",
    )

    def __init__(self) -> None:
        self._children: list[LayoutNode] = []
        self._parent: LayoutNode | None = None
        self._style: dict[str, Any] = {
            "width": None, "height": None,
            "minWidth": None, "minHeight": None,
            "maxWidth": None, "maxHeight": None,
            "marginTop": 0, "marginBottom": 0, "marginLeft": 0, "marginRight": 0,
            "paddingTop": 0, "paddingBottom": 0, "paddingLeft": 0, "paddingRight": 0,
            "borderTop": 0, "borderBottom": 0, "borderLeft": 0, "borderRight": 0,
            "flexGrow": 0, "flexShrink": 1, "flexBasis": None,
            "flexDirection": 0, "flexWrap": 0,
            "alignItems": 3, "alignSelf": 3, "justifyContent": 0,
            "position": 0, "display": 0, "overflow": 0,
            "gap": 0, "columnGap": 0, "rowGap": 0,
        }
        self._layout: dict[str, float] = {
            "x": 0, "y": 0, "width": 0, "height": 0,
        }
        self._measureFunc: Callable | None = None
        self._dirty = True

    # --- Child management ---
    def insertChild(self, child: LayoutNode, index: int) -> None:
        child._parent = self
        self._children.insert(index, child)
        self._dirty = True

    def removeChild(self, child: LayoutNode) -> None:
        child._parent = None
        try:
            self._children.remove(child)
        except ValueError:
            pass
        self._dirty = True

    @property
    def childCount(self) -> int:
        return len(self._children)

    def getChild(self, index: int) -> LayoutNode:
        return self._children[index]

    # --- Style setters ---
    def setWidth(self, w: float) -> None:
        self._style["width"] = w
        self._dirty = True

    def setHeight(self, h: float) -> None:
        self._style["height"] = h
        self._dirty = True

    def setMinWidth(self, w: float) -> None:
        self._style["minWidth"] = w
        self._dirty = True

    def setMinHeight(self, h: float) -> None:
        self._style["minHeight"] = h
        self._dirty = True

    def setMaxWidth(self, w: float) -> None:
        self._style["maxWidth"] = w
        self._dirty = True

    def setMaxHeight(self, h: float) -> None:
        self._style["maxHeight"] = h
        self._dirty = True

    def setWidthPercent(self, pct: float) -> None:
        self._style["widthPercent"] = pct
        self._dirty = True

    def setHeightPercent(self, pct: float) -> None:
        self._style["heightPercent"] = pct
        self._dirty = True

    def setMargin(self, edge: int, value: float) -> None:
        edges = ["marginTop", "marginBottom", "marginLeft", "marginRight"]
        self._style[edges[edge]] = value
        self._dirty = True

    def setPadding(self, edge: int, value: float) -> None:
        edges = ["paddingTop", "paddingBottom", "paddingLeft", "paddingRight"]
        self._style[edges[edge]] = value
        self._dirty = True

    def setBorder(self, edge: int, value: float) -> None:
        edges = ["borderTop", "borderBottom", "borderLeft", "borderRight"]
        self._style[edges[edge]] = value
        self._dirty = True

    def setFlexGrow(self, v: float) -> None:
        self._style["flexGrow"] = v
        self._dirty = True

    def setFlexShrink(self, v: float) -> None:
        self._style["flexShrink"] = v
        self._dirty = True

    def setFlexBasis(self, v: float) -> None:
        self._style["flexBasis"] = v
        self._dirty = True

    def setFlexBasisPercent(self, pct: float) -> None:
        self._style["flexBasisPercent"] = pct
        self._dirty = True

    def setFlexDirection(self, v: int) -> None:
        self._style["flexDirection"] = v
        self._dirty = True

    def setFlexWrap(self, v: int) -> None:
        self._style["flexWrap"] = v
        self._dirty = True

    def setAlignItems(self, v: int) -> None:
        self._style["alignItems"] = v
        self._dirty = True

    def setAlignSelf(self, v: int) -> None:
        self._style["alignSelf"] = v
        self._dirty = True

    def setJustifyContent(self, v: int) -> None:
        self._style["justifyContent"] = v
        self._dirty = True

    def setPositionType(self, v: int) -> None:
        self._style["position"] = v
        self._dirty = True

    def setPosition(self, edge: int, value: float) -> None:
        edges = ["positionTop", "positionBottom", "positionLeft", "positionRight"]
        self._style[edges[edge]] = value
        self._dirty = True

    def setPositionPercent(self, edge: int, pct: float) -> None:
        edges = ["positionTopPercent", "positionBottomPercent", "positionLeftPercent", "positionRightPercent"]
        self._style[edges[edge]] = pct
        self._dirty = True

    def setDisplay(self, v: int) -> None:
        self._style["display"] = v
        self._dirty = True

    def setOverflow(self, v: int) -> None:
        self._style["overflow"] = v
        self._dirty = True

    def setGap(self, gutter: int, value: float) -> None:
        if gutter == 0:
            self._style["columnGap"] = value
        else:
            self._style["rowGap"] = value
        self._dirty = True

    def setMeasureFunc(self, fn: Callable | None) -> None:
        self._measureFunc = fn
        self._dirty = True

    def unsetMeasureFunc(self) -> None:
        self._measureFunc = None

    # --- Layout computation ---
    def calculateLayout(self, width: float | None = None, height: float | None = None) -> None:
        if not self._dirty:
            return
        self._layout["width"] = width if width is not None else (self._style["width"] or 0)
        self._layout["height"] = height if height is not None else (self._style["height"] or 0)
        self._layout["x"] = 0
        self._layout["y"] = 0

        # Simple column layout
        current_y = self._style["paddingTop"] + self._style["borderTop"]
        available_w = max(0, self._layout["width"] - self._style["paddingLeft"] - self._style["paddingRight"] - self._style["borderLeft"] - self._style["borderRight"])

        for child in self._children:
            if self._style["display"] == 1:  # None
                continue
            child.calculateLayout(available_w)
            child._layout["x"] = self._style["paddingLeft"] + self._style["borderLeft"]
            child._layout["y"] = current_y
            current_y += child._layout["height"] + self._style["rowGap"]

        if self._children:
            current_y -= self._style["rowGap"]

        if self._style["height"] is None:
            self._layout["height"] = current_y + self._style["paddingBottom"] + self._style["borderBottom"]

        self._dirty = False

    # --- Computed layout getters ---
    def getComputedWidth(self) -> float:
        return self._layout["width"]

    def getComputedHeight(self) -> float:
        return self._layout["height"]

    def getComputedLeft(self) -> float:
        return self._layout["x"]

    def getComputedTop(self) -> float:
        return self._layout["y"]

    def getComputedPadding(self, edge: int) -> float:
        edges = ["paddingTop", "paddingBottom", "paddingLeft", "paddingRight"]
        return self._style.get(edges[edge], 0)

    def getComputedBorder(self, edge: int) -> float:
        edges = ["borderTop", "borderBottom", "borderLeft", "borderRight"]
        return self._style.get(edges[edge], 0)

    def getComputedMargin(self, edge: int) -> float:
        edges = ["marginTop", "marginBottom", "marginLeft", "marginRight"]
        return self._style.get(edges[edge], 0)

    # --- Lifecycle ---
    def freeRecursive(self) -> None:
        for child in self._children:
            child.freeRecursive()
        self._children.clear()
        self._parent = None
        self._measureFunc = None


def createLayoutNode() -> LayoutNode:
    return LayoutNode()


create_layout_node = createLayoutNode
