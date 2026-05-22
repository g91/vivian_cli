"""Port of src/ink/squash-text-nodes.ts."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .dom import DOMElement

from .styles import TextStyles

StyledSegment = dict[str, Any]


def squashTextNodesToSegments(
    node: DOMElement,
    inheritedStyles: TextStyles = None,
    inheritedHyperlink: str | None = None,
    out: list[StyledSegment] | None = None,
) -> list[StyledSegment]:
    if inheritedStyles is None:
        inheritedStyles = {}
    if out is None:
        out = []

    merged_styles = {**inheritedStyles, **(getattr(node, "textStyles", None) or {})}

    for child in getattr(node, "childNodes", []):
        if child is None:
            continue
        node_name = getattr(child, "nodeName", "")

        if node_name == "#text":
            node_value = getattr(child, "nodeValue", "")
            if node_value:
                out.append({
                    "text": node_value,
                    "styles": merged_styles,
                    "hyperlink": inheritedHyperlink,
                })
        elif node_name in ("ink-text", "ink-virtual-text"):
            squashTextNodesToSegments(child, merged_styles, inheritedHyperlink, out)
        elif node_name == "ink-link":
            href = getattr(child, "attributes", {}).get("href")
            squashTextNodesToSegments(child, merged_styles, href or inheritedHyperlink, out)

    return out


def squashTextNodes(node: DOMElement) -> str:
    text = ""
    for child in getattr(node, "childNodes", []):
        if child is None:
            continue
        node_name = getattr(child, "nodeName", "")
        if node_name == "#text":
            text += getattr(child, "nodeValue", "")
        elif node_name in ("ink-text", "ink-virtual-text", "ink-link"):
            text += squashTextNodes(child)
    return text


squash_text_nodes_to_segments = squashTextNodesToSegments
squash_text_nodes = squashTextNodes
