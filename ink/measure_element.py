"""Port of src/ink/measure-element.ts."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .dom import DOMElement


def measureElement(node: DOMElement) -> dict[str, int]:
    yoga = getattr(node, "yogaNode", None)
    return {
        "width": yoga.getComputedWidth() if yoga else 0,
        "height": yoga.getComputedHeight() if yoga else 0,
    }


measure_element = measureElement
