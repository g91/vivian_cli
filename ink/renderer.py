"""Port of src/ink/renderer.ts."""
from __future__ import annotations

import math
from typing import Any, Callable

from .dom import DOMElement, markDirty
from .frame import Frame, Cursor, Size
from .node_cache import consumeAbsoluteRemovedFlag
from .output import Output
from .screen import createScreen, StylePool, CharPool, HyperlinkPool

RenderOptions = dict[str, Any]
Renderer = Callable[[RenderOptions], Frame]


def createRenderer(node: DOMElement, stylePool: StylePool) -> Renderer:
    output: Output | None = None

    def render(options: RenderOptions) -> Frame:
        nonlocal output

        frontFrame = options["frontFrame"]
        backFrame = options["backFrame"]
        isTTY = options.get("isTTY", True)
        terminalWidth = options.get("terminalWidth", 80)
        terminalRows = options.get("terminalRows", 24)
        altScreen = options.get("altScreen", False)
        prevFrameContaminated = options.get("prevFrameContaminated", False)

        prevScreen = frontFrame.screen
        backScreen = backFrame.screen
        charPool = backScreen.charPool
        hyperlinkPool = backScreen.hyperlinkPool

        yoga = node.yogaNode
        if not yoga:
            return Frame(
                screen=createScreen(terminalWidth, 0, stylePool, charPool, hyperlinkPool),
                viewport=Size(width=terminalWidth, height=terminalRows),
                cursor=Cursor(x=0, y=0, visible=True),
            )

        computedHeight = yoga.getComputedHeight()
        computedWidth = yoga.getComputedWidth()

        if (computedHeight is None or not math.isfinite(computedHeight) or computedHeight < 0 or
            computedWidth is None or not math.isfinite(computedWidth) or computedWidth < 0):
            return Frame(
                screen=createScreen(terminalWidth, 0, stylePool, charPool, hyperlinkPool),
                viewport=Size(width=terminalWidth, height=terminalRows),
                cursor=Cursor(x=0, y=0, visible=True),
            )

        width = int(computedWidth)
        yogaHeight = int(computedHeight)
        height = terminalRows if altScreen else yogaHeight

        screen = backScreen if backScreen else createScreen(width, height, stylePool, charPool, hyperlinkPool)

        if output:
            output.reset(width, height, screen)
        else:
            output = Output(width, height, stylePool, screen)

        absoluteRemoved = consumeAbsoluteRemovedFlag()
        from .render_node_to_output import renderNodeToOutput
        renderNodeToOutput(node, output, {
            "prevScreen": None if (absoluteRemoved or prevFrameContaminated) else prevScreen,
        })

        renderedScreen = output.get()

        return Frame(
            screen=renderedScreen,
            viewport=Size(
                width=terminalWidth,
                height=terminalRows + 1 if altScreen else terminalRows,
            ),
            cursor=Cursor(
                x=0,
                y=max(0, min(renderedScreen.height, terminalRows) - 1) if altScreen else renderedScreen.height,
                visible=not isTTY or renderedScreen.height == 0,
            ),
        )

    return render
