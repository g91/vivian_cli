"""Port of src/ink/components/Box.tsx."""
from __future__ import annotations

from typing import Any

from ..dom import DOMElement, createNode, setStyle
from ..styles import applyStyles


def createBox(props: dict[str, Any] | None = None) -> DOMElement:
    props = props or {}
    node = createNode("ink-box")
    style = props.get("style", {})
    setStyle(node, style)
    if node.yogaNode:
        applyStyles(node.yogaNode, style)
    for key, value in props.items():
        if key not in ("style", "children"):
            node.attributes[key] = value
    return node
