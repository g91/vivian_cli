"""Port of src/ink/components/Text.tsx."""
from __future__ import annotations

from typing import Any

from ..dom import DOMElement, createNode, setStyle, setTextStyles
from ..styles import applyStyles


def createText(props: dict[str, Any] | None = None) -> DOMElement:
    props = props or {}
    node = createNode("ink-text")
    style = props.get("style", {})
    setStyle(node, style)
    if node.yogaNode:
        applyStyles(node.yogaNode, style)
    text_styles = props.get("textStyles")
    if text_styles:
        setTextStyles(node, text_styles)
    for key, value in props.items():
        if key not in ("style", "children", "textStyles"):
            node.attributes[key] = value
    return node
