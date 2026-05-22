"""Port of src/ink/hit-test.ts."""
from __future__ import annotations

from typing import Any

from .dom import DOMElement
from .events.click_event import ClickEvent
from .node_cache import getCachedLayout


def hitTest(node: DOMElement, col: int, row: int) -> DOMElement | None:
    rect = getCachedLayout(node)
    if not rect:
        return None
    if col < rect["x"] or col >= rect["x"] + rect["width"] or row < rect["y"] or row >= rect["y"] + rect["height"]:
        return None
    for child in reversed(node.childNodes):
        if child.nodeName == "#text":
            continue
        hit = hitTest(child, col, row)
        if hit:
            return hit
    return node


def dispatchClick(root: DOMElement, col: int, row: int, cellIsBlank: bool = False) -> bool:
    target = hitTest(root, col, row)
    if not target:
        return False

    if root.focusManager:
        ft = target
        while ft:
            if isinstance(ft.attributes.get("tabIndex"), (int, float)):
                root.focusManager.handleClickFocus(ft)
                break
            ft = ft.parentNode

    event = ClickEvent(col, row, cellIsBlank)
    handled = False
    t = target
    while t:
        handlers = getattr(t, "_eventHandlers", None)
        handler = handlers.get("onClick") if handlers else None
        if handler:
            handled = True
            rect = getCachedLayout(t)
            if rect:
                event.localCol = col - rect["x"]
                event.localRow = row - rect["y"]
            handler(event)
            if event.didStopImmediatePropagation():
                return True
        t = t.parentNode
    return handled


def dispatchHover(root: DOMElement, col: int, row: int, hovered: set[DOMElement]) -> None:
    next_set: set[DOMElement] = set()
    node = hitTest(root, col, row)
    while node:
        h = getattr(node, "_eventHandlers", None)
        if h and (h.get("onMouseEnter") or h.get("onMouseLeave")):
            next_set.add(node)
        node = node.parentNode

    for old in list(hovered):
        if old not in next_set:
            hovered.discard(old)
            if old.parentNode:
                h = getattr(old, "_eventHandlers", None)
                if h and h.get("onMouseLeave"):
                    h["onMouseLeave"]()

    for n in next_set:
        if n not in hovered:
            hovered.add(n)
            h = getattr(n, "_eventHandlers", None)
            if h and h.get("onMouseEnter"):
                h["onMouseEnter"]()
