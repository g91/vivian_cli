"""
Port of src/utils/horizontalScroll.ts
"""
from __future__ import annotations

from typing import Any, Dict, List


HorizontalScrollWindow = Dict[str, Any]


def calculateHorizontalScrollWindow(itemWidths, availableWidth, arrowWidth, selectedIdx, firstItemHasSeparator = True):
    """Calculate the visible window of items that fit within available width,
ensuring the selected item is always visible. Uses edge-based scrolling:
the window only scrolls when the selected item would be outside the visible
range, and positions the selected item at the edge (not centered).

@param itemWidths - Array of item widths (each width should include separator if applicable)
@param availableWidth - Total available width for items
@param arrowWidth - Width of scroll indicator arrow (including space)
@param selectedIdx - Index of selected item (must stay visible)
@param firstItemHasSeparator - Whether first item's width includes a separator that should be ignored
@returns Visible window bounds and whether to show scroll arrows"""
    total_items = len(itemWidths)

    if total_items == 0:
        return {
            "startIndex": 0,
            "endIndex": 0,
            "showLeftArrow": False,
            "showRightArrow": False,
        }

    clamped_selected = max(0, min(selectedIdx, total_items - 1))
    total_width = sum(itemWidths)
    if total_width <= availableWidth:
        return {
            "startIndex": 0,
            "endIndex": total_items,
            "showLeftArrow": False,
            "showRightArrow": False,
        }

    cumulative_widths = [0]
    for width in itemWidths:
        cumulative_widths.append(cumulative_widths[-1] + width)

    def range_width(start: int, end: int) -> int:
        base_width = cumulative_widths[end] - cumulative_widths[start]
        if firstItemHasSeparator and start > 0:
            return base_width - 1
        return base_width

    def effective_width(start: int, end: int) -> int:
        width = availableWidth
        if start > 0:
            width -= arrowWidth
        if end < total_items:
            width -= arrowWidth
        return width

    start_index = 0
    end_index = 1
    while (
        end_index < total_items
        and range_width(start_index, end_index + 1)
        <= effective_width(start_index, end_index + 1)
    ):
        end_index += 1

    if start_index <= clamped_selected < end_index:
        return {
            "startIndex": start_index,
            "endIndex": end_index,
            "showLeftArrow": start_index > 0,
            "showRightArrow": end_index < total_items,
        }

    if clamped_selected >= end_index:
        end_index = clamped_selected + 1
        start_index = clamped_selected
        while (
            start_index > 0
            and range_width(start_index - 1, end_index)
            <= effective_width(start_index - 1, end_index)
        ):
            start_index -= 1
    else:
        start_index = clamped_selected
        end_index = clamped_selected + 1
        while (
            end_index < total_items
            and range_width(start_index, end_index + 1)
            <= effective_width(start_index, end_index + 1)
        ):
            end_index += 1

    return {
        "startIndex": start_index,
        "endIndex": end_index,
        "showLeftArrow": start_index > 0,
        "showRightArrow": end_index < total_items,
    }


calculate_horizontal_scroll_window = calculateHorizontalScrollWindow

