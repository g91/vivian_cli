"""Port of src/ink/components/ScrollBox.tsx."""
from __future__ import annotations

from typing import Any

from ..dom import DOMElement, createNode, setStyle
from ..styles import applyStyles


def createScrollBox(props: dict[str, Any] | None = None) -> DOMElement:
    props = props or {}
    node = createNode("ink-box")
    style = {**props.get("style", {}), "overflowY": "scroll"}
    setStyle(node, style)
    if node.yogaNode:
        applyStyles(node.yogaNode, style)
    node.scrollTop = 0
    node.stickyScroll = props.get("stickyScroll", False)
    for key, value in props.items():
        if key not in ("style", "children", "stickyScroll"):
            node.attributes[key] = value
    return node
