"""Port of src/ink/dom.ts."""
from __future__ import annotations

from typing import Any, Callable

from .styles import Styles, TextStyles

TextName = "#text"
ElementNames = (
    "ink-root", "ink-box", "ink-text", "ink-virtual-text",
    "ink-link", "ink-progress", "ink-raw-ansi",
)
NodeNames = ElementNames + (TextName,)


class DOMElement:
    __slots__ = (
        "nodeName", "attributes", "childNodes", "textStyles",
        "parentNode", "yogaNode", "style", "dirty", "isHidden",
        "_eventHandlers", "onComputeLayout", "onRender", "onImmediateRender",
        "hasRenderedContent", "scrollTop", "pendingScrollDelta",
        "scrollClampMin", "scrollClampMax", "scrollHeight",
        "scrollViewportHeight", "scrollViewportTop", "stickyScroll",
        "scrollAnchor", "focusManager", "debugOwnerChain",
    )

    def __init__(self, nodeName: ElementNames) -> None:
        self.nodeName = nodeName
        self.attributes: dict[str, Any] = {}
        self.childNodes: list[DOMNode] = []
        self.textStyles: TextStyles | None = None
        self.parentNode: DOMElement | None = None
        self.yogaNode: Any = None
        self.style: Styles = {}
        self.dirty = False
        self.isHidden: bool | None = None
        self._eventHandlers: dict[str, Any] | None = None
        self.onComputeLayout: Callable[[], None] | None = None
        self.onRender: Callable[[], None] | None = None
        self.onImmediateRender: Callable[[], None] | None = None
        self.hasRenderedContent: bool | None = None
        self.scrollTop: int | None = None
        self.pendingScrollDelta: int | None = None
        self.scrollClampMin: int | None = None
        self.scrollClampMax: int | None = None
        self.scrollHeight: int | None = None
        self.scrollViewportHeight: int | None = None
        self.scrollViewportTop: int | None = None
        self.stickyScroll: bool | None = None
        self.scrollAnchor: dict[str, Any] | None = None
        self.focusManager: Any = None
        self.debugOwnerChain: list[str] | None = None


class TextNode:
    __slots__ = ("nodeName", "nodeValue", "parentNode", "yogaNode", "style")

    def __init__(self, text: str) -> None:
        self.nodeName: TextName = "#text"
        self.nodeValue = text
        self.parentNode: DOMElement | None = None
        self.yogaNode: Any = None
        self.style: Styles = {}


DOMNode = DOMElement | TextNode


def createNode(nodeName: ElementNames) -> DOMElement:
    needs_yoga = nodeName not in ("ink-virtual-text", "ink-link", "ink-progress")
    node = DOMElement(nodeName)
    if needs_yoga:
        from .layout.node import createLayoutNode
        node.yogaNode = createLayoutNode()
    return node


def appendChildNode(node: DOMElement, childNode: DOMNode) -> None:
    if childNode.parentNode:
        removeChildNode(childNode.parentNode, childNode)
    childNode.parentNode = node
    node.childNodes.append(childNode)
    if childNode.yogaNode and node.yogaNode:
        idx = len(node.childNodes) - 1
        node.yogaNode.insertChild(childNode.yogaNode, idx)
    markDirty(node)


def insertBeforeNode(node: DOMElement, newChildNode: DOMNode, beforeChildNode: DOMNode) -> None:
    if newChildNode.parentNode:
        removeChildNode(newChildNode.parentNode, newChildNode)
    newChildNode.parentNode = node
    try:
        index = node.childNodes.index(beforeChildNode)
    except ValueError:
        index = len(node.childNodes)
    node.childNodes.insert(index, newChildNode)
    if newChildNode.yogaNode:
        node.yogaNode.insertChild(newChildNode.yogaNode, index)
    markDirty(node)


def removeChildNode(node: DOMElement, removeNode: DOMNode) -> None:
    if removeNode.yogaNode:
        node.yogaNode.removeChild(removeNode.yogaNode)
    removeNode.parentNode = None
    try:
        node.childNodes.remove(removeNode)
    except ValueError:
        pass
    markDirty(node)


def setAttribute(node: DOMElement, key: str, value: Any) -> None:
    if key == "children":
        return
    if node.attributes.get(key) == value:
        return
    node.attributes[key] = value
    markDirty(node)


def setStyle(node: DOMNode, style: Styles) -> None:
    if _stylesEqual(node.style, style):
        return
    node.style = style
    markDirty(node)


def setTextStyles(node: DOMElement, textStyles: TextStyles) -> None:
    if _shallowEqual(node.textStyles, textStyles):
        return
    node.textStyles = textStyles
    markDirty(node)


def createTextNode(text: str) -> TextNode:
    node = TextNode(text)
    return node


def setTextNodeValue(node: TextNode, text: str) -> None:
    if node.nodeValue == text:
        return
    node.nodeValue = text
    markDirty(node)


def markDirty(node: DOMNode | None = None) -> None:
    current = node
    while current:
        if current.nodeName != "#text":
            current.dirty = True
        current = current.parentNode


def scheduleRenderFrom(node: DOMNode | None = None) -> None:
    cur = node
    while cur and cur.parentNode:
        cur = cur.parentNode
    if cur and cur.nodeName != "#text" and cur.onRender:
        cur.onRender()


def clearYogaNodeReferences(node: DOMElement | TextNode) -> None:
    if node.yogaNode:
        node.yogaNode = None
    if node.nodeName != "#text":
        for child in node.childNodes:
            clearYogaNodeReferences(child)


def findOwnerChainAtRow(root: DOMElement, y: int) -> list[str]:
    return _find_chain_at(root, y, 0)


def _find_chain_at(node: DOMElement, target_y: int, current_y: int) -> list[str]:
    yoga = node.yogaNode
    if not yoga:
        return []
    top = yoga.getComputedTop()
    height = yoga.getComputedHeight()
    if target_y < top or target_y >= top + height:
        return []
    for child in reversed(node.childNodes):
        if child.nodeName == "#text":
            continue
        chain = _find_chain_at(child, target_y, top)
        if chain:
            return chain
    return node.debugOwnerChain or []


def _stylesEqual(a: Styles, b: Styles) -> bool:
    return _shallowEqual(a, b)


def _shallowEqual(a: Any, b: Any) -> bool:
    if a is b:
        return True
    if a is None or b is None:
        return False
    if isinstance(a, dict) and isinstance(b, dict):
        if len(a) != len(b):
            return False
        for k in a:
            if k not in b or a[k] != b[k]:
                return False
        return True
    return a == b


create_node = createNode
append_child_node = appendChildNode
insert_before_node = insertBeforeNode
remove_child_node = removeChildNode
set_attribute = setAttribute
set_style = setStyle
set_text_styles = setTextStyles
create_text_node = createTextNode
set_text_node_value = setTextNodeValue
mark_dirty = markDirty
schedule_render_from = scheduleRenderFrom
clear_yoga_node_references = clearYogaNodeReferences
find_owner_chain_at_row = findOwnerChainAtRow
