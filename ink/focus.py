"""Port of src/ink/focus.ts."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from .dom import DOMElement

MAX_FOCUS_STACK = 32


class FocusEvent:
    __slots__ = ("type", "relatedTarget")
    def __init__(self, type: str, relatedTarget: Any = None) -> None:
        self.type = type
        self.relatedTarget = relatedTarget


class FocusManager:
    __slots__ = ("activeElement", "_dispatchFocusEvent", "_enabled", "_focusStack")

    def __init__(self, dispatchFocusEvent: Callable[[DOMElement, FocusEvent], bool]) -> None:
        self.activeElement: DOMElement | None = None
        self._dispatchFocusEvent = dispatchFocusEvent
        self._enabled = True
        self._focusStack: list[DOMElement] = []

    def focus(self, node: DOMElement) -> None:
        if node is self.activeElement:
            return
        if not self._enabled:
            return

        previous = self.activeElement
        if previous:
            idx = -1
            try:
                idx = self._focusStack.index(previous)
            except ValueError:
                pass
            if idx != -1:
                self._focusStack.pop(idx)
            self._focusStack.append(previous)
            if len(self._focusStack) > MAX_FOCUS_STACK:
                self._focusStack.pop(0)
            self._dispatchFocusEvent(previous, FocusEvent("blur", node))
        self.activeElement = node
        self._dispatchFocusEvent(node, FocusEvent("focus", previous))

    def blur(self) -> None:
        if not self.activeElement:
            return
        previous = self.activeElement
        self.activeElement = None
        self._dispatchFocusEvent(previous, FocusEvent("blur", None))

    def handleNodeRemoved(self, node: DOMElement, root: DOMElement) -> None:
        self._focusStack = [n for n in self._focusStack if n is not node and _isInTree(n, root)]
        if not self.activeElement:
            return
        if self.activeElement is not node and _isInTree(self.activeElement, root):
            return
        removed = self.activeElement
        self.activeElement = None
        self._dispatchFocusEvent(removed, FocusEvent("blur", None))
        while self._focusStack:
            candidate = self._focusStack.pop()
            if _isInTree(candidate, root):
                self.activeElement = candidate
                self._dispatchFocusEvent(candidate, FocusEvent("focus", removed))
                return

    def handleAutoFocus(self, node: DOMElement) -> None:
        self.focus(node)

    def handleClickFocus(self, node: DOMElement) -> None:
        tab_index = node.attributes.get("tabIndex")
        if not isinstance(tab_index, (int, float)):
            return
        self.focus(node)

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False

    def focusNext(self, root: DOMElement) -> None:
        self._moveFocus(1, root)

    def focusPrevious(self, root: DOMElement) -> None:
        self._moveFocus(-1, root)

    def _moveFocus(self, direction: int, root: DOMElement) -> None:
        if not self._enabled:
            return
        tabbable = _collectTabbable(root)
        if not tabbable:
            return
        try:
            current_index = tabbable.index(self.activeElement) if self.activeElement else -1
        except ValueError:
            current_index = -1
        if current_index == -1:
            next_index = 0 if direction == 1 else len(tabbable) - 1
        else:
            next_index = (current_index + direction) % len(tabbable)
        next_node = tabbable[next_index]
        if next_node:
            self.focus(next_node)


def _collectTabbable(root: DOMElement) -> list[DOMElement]:
    result: list[DOMElement] = []
    _walkTree(root, result)
    return result


def _walkTree(node: DOMElement, result: list[DOMElement]) -> None:
    tab_index = node.attributes.get("tabIndex")
    if isinstance(tab_index, (int, float)) and tab_index >= 0:
        result.append(node)
    for child in node.childNodes:
        if child.nodeName != "#text":
            _walkTree(child, result)


def _isInTree(node: DOMElement, root: DOMElement) -> bool:
    current: DOMElement | None = node
    while current:
        if current is root:
            return True
        current = current.parentNode
    return False


def getRootNode(node: DOMElement) -> DOMElement:
    current: DOMElement | None = node
    while current:
        if current.focusManager:
            return current
        current = current.parentNode
    raise RuntimeError("Node is not in a tree with a FocusManager")


def getFocusManager(node: DOMElement) -> FocusManager:
    return getRootNode(node).focusManager


get_root_node = getRootNode
get_focus_manager = getFocusManager
