"""Port of src/ink/components/NoSelect.tsx."""
from __future__ import annotations

from typing import Any

from ..dom import DOMElement, createNode, setStyle


def createNoSelect(props: dict[str, Any] | None = None) -> DOMElement:
    props = props or {}
    node = createNode("ink-box")
    style = {**props.get("style", {}), "noSelect": True}
    setStyle(node, style)
    return node
