"""Port of src/ink/frame.ts."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .screen import Screen, createScreen, StylePool, CharPool, HyperlinkPool


@dataclass
class Cursor:
    x: int = 0
    y: int = 0
    visible: bool = True


@dataclass
class Size:
    width: int = 0
    height: int = 0


@dataclass
class Frame:
    screen: Screen
    viewport: Size
    cursor: Cursor
    scrollHint: dict[str, int] | None = None
    scrollDrainPending: bool = False


FlickerReason = str  # 'resize' | 'offscreen' | 'clear'


@dataclass
class FrameEvent:
    durationMs: float = 0
    phases: dict[str, Any] | None = None
    flickers: list[dict[str, Any]] = field(default_factory=list)


Patch = dict[str, Any]
Diff = list[Patch]


def emptyFrame(
    rows: int, columns: int,
    stylePool: StylePool, charPool: CharPool, hyperlinkPool: HyperlinkPool,
) -> Frame:
    return Frame(
        screen=createScreen(0, 0, stylePool, charPool, hyperlinkPool),
        viewport=Size(width=columns, height=rows),
        cursor=Cursor(x=0, y=0, visible=True),
    )


def shouldClearScreen(prevFrame: Frame, frame: Frame) -> FlickerReason | None:
    did_resize = (
        frame.viewport.height != prevFrame.viewport.height
        or frame.viewport.width != prevFrame.viewport.width
    )
    if did_resize:
        return "resize"

    current_overflows = frame.screen.height >= frame.viewport.height
    previous_overflowed = prevFrame.screen.height >= prevFrame.viewport.height
    if current_overflows or previous_overflowed:
        return "offscreen"

    return None


empty_frame = emptyFrame
should_clear_screen = shouldClearScreen
