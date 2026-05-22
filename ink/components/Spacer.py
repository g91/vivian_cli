"""Port of src/ink/components/Spacer.tsx."""
from __future__ import annotations

from typing import Any

from ..dom import DOMElement, createNode, setStyle


def createSpacer(props: dict[str, Any] | None = None) -> DOMElement:
    props = props or {}
    node = createNode("ink-box")
    style = {**props.get("style", {}), "flexGrow": 1}
    setStyle(node, style)
    return node
