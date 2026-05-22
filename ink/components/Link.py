"""Port of src/ink/components/Link.tsx."""
from __future__ import annotations

from typing import Any

from ..dom import DOMElement, createNode, setStyle


def createLink(props: dict[str, Any] | None = None) -> DOMElement:
    props = props or {}
    node = createNode("ink-link")
    style = props.get("style", {})
    setStyle(node, style)
    for key, value in props.items():
        if key not in ("style", "children"):
            node.attributes[key] = value
    return node
