"""Port of src/ink/components/Newline.tsx."""
from __future__ import annotations

from ..dom import DOMElement, createTextNode


def createNewline() -> DOMElement:
    from ..dom import createNode
    node = createNode("ink-text")
    text_node = createTextNode("\n")
    node.childNodes.append(text_node)
    return node
