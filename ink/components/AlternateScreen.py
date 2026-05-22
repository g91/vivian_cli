"""Port of src/ink/components/AlternateScreen.tsx."""
from __future__ import annotations

from typing import Any

from ..dom import DOMElement, createNode, setStyle


def createAlternateScreen(props: dict[str, Any] | None = None) -> DOMElement:
    props = props or {}
    node = createNode("ink-box")
    style = props.get("style", {})
    setStyle(node, style)
    return node
