"""Port of src/ink/get-max-width.ts."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .layout.node import LayoutNode


def getMaxWidth(yogaNode: LayoutNode) -> int:
    return (
        yogaNode.getComputedWidth()
        - yogaNode.getComputedPadding(0)  # Left
        - yogaNode.getComputedPadding(2)  # Right
        - yogaNode.getComputedBorder(0)   # Left
        - yogaNode.getComputedBorder(2)   # Right
    )


get_max_width = getMaxWidth
