"""Port of src/ink/styles.ts."""
from __future__ import annotations

from typing import Any, Literal

RGBColor = str  # f"rgb({r},{g},{b})"
HexColor = str  # f"#{hex}"
Ansi256Color = str  # f"ansi256({n})"
AnsiColor = str  # f"ansi:{name}"

Color = RGBColor | HexColor | Ansi256Color | AnsiColor

TextStyles = dict[str, Any]

Styles = dict[str, Any]

BorderStyle = str | dict[str, str]

BorderTextOptions = dict[str, Any]


def applyPositionStyles(node: Any, style: Styles) -> None:
    if "position" in style:
        node.setPositionType(1 if style["position"] == "absolute" else 0)
    for edge in ("top", "bottom", "left", "right"):
        if edge in style:
            _applyPositionEdge(node, edge, style[edge])


def _applyPositionEdge(node: Any, edge: str, v: int | str | None) -> None:
    if v is None:
        return
    edge_map = {"top": 0, "bottom": 1, "left": 2, "right": 3}
    if isinstance(v, str) and v.endswith("%"):
        node.setPositionPercent(edge_map[edge], float(v[:-1]))
    elif isinstance(v, (int, float)):
        node.setPosition(edge_map[edge], float(v))


def applyOverflowStyles(node: Any, style: Styles) -> None:
    y = style.get("overflowY", style.get("overflow"))
    x = style.get("overflowX", style.get("overflow"))
    if y == "hidden" or y == "scroll":
        node.setOverflow(1)  # Hidden
    elif y == "visible":
        node.setOverflow(0)


def applyMarginStyles(node: Any, style: Styles) -> None:
    if "margin" in style:
        node.setMargin(0, style["margin"])
    if "marginX" in style:
        node.setMargin(2, style["marginX"])
        node.setMargin(3, style["marginX"])
    if "marginY" in style:
        node.setMargin(0, style["marginY"])
        node.setMargin(1, style["marginY"])
    for i, edge in enumerate(("marginTop", "marginBottom", "marginLeft", "marginRight")):
        if edge in style:
            node.setMargin(i, style[edge])


def applyPaddingStyles(node: Any, style: Styles) -> None:
    if "padding" in style:
        node.setPadding(0, style["padding"])
    if "paddingX" in style:
        node.setPadding(2, style["paddingX"])
        node.setPadding(3, style["paddingX"])
    if "paddingY" in style:
        node.setPadding(0, style["paddingY"])
        node.setPadding(1, style["paddingY"])
    for i, edge in enumerate(("paddingTop", "paddingBottom", "paddingLeft", "paddingRight")):
        if edge in style:
            node.setPadding(i, style[edge])


def applyFlexStyles(node: Any, style: Styles) -> None:
    if "flexGrow" in style:
        node.setFlexGrow(style["flexGrow"])
    if "flexShrink" in style:
        node.setFlexShrink(style["flexShrink"])
    if "flexDirection" in style:
        dirs = {"row": 0, "column": 1, "row-reverse": 2, "column-reverse": 3}
        node.setFlexDirection(dirs.get(style["flexDirection"], 0))
    if "flexBasis" in style:
        v = style["flexBasis"]
        if isinstance(v, str) and v.endswith("%"):
            node.setFlexBasisPercent(float(v[:-1]))
        else:
            node.setFlexBasis(float(v))
    if "flexWrap" in style:
        wraps = {"nowrap": 0, "wrap": 1, "wrap-reverse": 2}
        node.setFlexWrap(wraps.get(style["flexWrap"], 0))
    if "alignItems" in style:
        aligns = {"flex-start": 0, "center": 1, "flex-end": 2, "stretch": 3}
        node.setAlignItems(aligns.get(style["alignItems"], 3))
    if "alignSelf" in style:
        aligns = {"flex-start": 0, "center": 1, "flex-end": 2, "auto": 3}
        node.setAlignSelf(aligns.get(style["alignSelf"], 3))
    if "justifyContent" in style:
        justifies = {"flex-start": 0, "flex-end": 1, "center": 2, "space-between": 3, "space-around": 4, "space-evenly": 5}
        node.setJustifyContent(justifies.get(style["justifyContent"], 0))


def applyDimensionStyles(node: Any, style: Styles) -> None:
    for attr, setter in (
        ("width", "setWidth"), ("height", "setHeight"),
        ("minWidth", "setMinWidth"), ("minHeight", "setMinHeight"),
        ("maxWidth", "setMaxWidth"), ("maxHeight", "setMaxHeight"),
    ):
        if attr in style:
            v = style[attr]
            if isinstance(v, str) and v.endswith("%"):
                getattr(node, f"{setter}Percent")(float(v[:-1]))
            elif isinstance(v, (int, float)):
                getattr(node, setter)(float(v))


def applyDisplayStyles(node: Any, style: Styles) -> None:
    if style.get("display") == "none":
        node.setDisplay(1)  # None
    else:
        node.setDisplay(0)  # Flex


def applyBorderStyles(node: Any, style: Styles, resolvedStyle: Styles | None = None) -> None:
    show_top = style.get("borderTop", True)
    show_bottom = style.get("borderBottom", True)
    show_left = style.get("borderLeft", True)
    show_right = style.get("borderRight", True)
    if show_top:
        node.setBorder(0, 1)
    if show_bottom:
        node.setBorder(1, 1)
    if show_left:
        node.setBorder(2, 1)
    if show_right:
        node.setBorder(3, 1)


def applyGapStyles(node: Any, style: Styles) -> None:
    if "gap" in style:
        node.setGap(0, style["gap"])
        node.setGap(1, style["gap"])
    if "columnGap" in style:
        node.setGap(0, style["columnGap"])
    if "rowGap" in style:
        node.setGap(1, style["rowGap"])


def applyStyles(node: Any, style: Styles = None, resolvedStyle: Styles | None = None) -> None:
    if style is None:
        style = {}
    applyPositionStyles(node, style)
    applyOverflowStyles(node, style)
    applyMarginStyles(node, style)
    applyPaddingStyles(node, style)
    applyFlexStyles(node, style)
    applyDimensionStyles(node, style)
    applyDisplayStyles(node, style)
    applyBorderStyles(node, style, resolvedStyle)
    applyGapStyles(node, style)


apply_styles = applyStyles
