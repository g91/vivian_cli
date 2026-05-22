"""Progress bar component — mirrors src/components/design-system/ProgressBar.tsx."""

from __future__ import annotations


BLOCKS = [' ', '▏', '▎', '▍', '▌', '▋', '▊', '▉', '█']


def ProgressBar(ratio: float, width: int, fillColor: str | None = None, emptyColor: str | None = None) -> str:
    del fillColor, emptyColor
    clamped_ratio = min(1.0, max(0.0, ratio))
    whole = int(clamped_ratio * width)
    segments = [BLOCKS[-1] * whole]
    if whole < width:
        remainder = clamped_ratio * width - whole
        middle = int(remainder * len(BLOCKS))
        middle = min(middle, len(BLOCKS) - 1)
        segments.append(BLOCKS[middle])
        empty = width - whole - 1
        if empty > 0:
            segments.append(BLOCKS[0] * empty)
    return "".join(segments)


__all__ = ["ProgressBar", "BLOCKS"]