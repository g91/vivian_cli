"""Port of src/ink/ink.tsx."""
from __future__ import annotations

import io
import sys
import threading
from dataclasses import dataclass
from typing import Any, Callable

from .components.App import App
from .components.CursorDeclarationContext import CursorDeclaration
from .dom import DOMElement, TextNode, appendChildNode, createNode, createTextNode, removeChildNode
from .focus import FocusManager
from .frame import FrameEvent, emptyFrame
from .instances import delete_instance
from .log_update import LogUpdate
from .renderer import createRenderer
from .reconciler import reconciler
from .screen import CharPool, HyperlinkPool, StylePool
from .selection import createSelectionState
from .terminal import writeDiffToTerminal


@dataclass(slots=True)
class Options:
    stdout: Any = sys.stdout
    stdin: Any = sys.stdin
    stderr: Any = sys.stderr
    exitOnCtrlC: bool = True
    patchConsole: bool = True
    waitUntilExit: Callable[[], Any] | None = None
    onFrame: Callable[[FrameEvent], None] | None = None


class Ink:
    def __init__(self, options: Options) -> None:
        self.options = options
        self.terminal = {"stdout": options.stdout, "stderr": options.stderr}
        self.terminalColumns = int(getattr(options.stdout, "columns", 80) or 80)
        self.terminalRows = int(getattr(options.stdout, "rows", 24) or 24)
        self.stylePool = StylePool()
        self.charPool = CharPool()
        self.hyperlinkPool = HyperlinkPool()
        self.frontFrame = emptyFrame(self.terminalRows, self.terminalColumns, self.stylePool, self.charPool, self.hyperlinkPool)
        self.backFrame = emptyFrame(self.terminalRows, self.terminalColumns, self.stylePool, self.charPool, self.hyperlinkPool)
        self.log = LogUpdate(bool(getattr(options.stdout, "isatty", lambda: False)()), self.stylePool)
        self.rootNode = createNode("ink-root")
        self.rootNode.focusManager = FocusManager(lambda target, event: reconciler.discreteUpdates(lambda: True))
        self.renderer = createRenderer(self.rootNode, self.stylePool)
        self.currentNode: Any = None
        self.isUnmounted = False
        self.selection = createSelectionState()
        self.searchHighlightQuery = ""
        self.cursorDeclaration: CursorDeclaration | None = None
        self._exit_event = threading.Event()
        self.app = App(
            stdin=options.stdin,
            stdout=options.stdout,
            stderr=options.stderr,
            exitOnCtrlC=options.exitOnCtrlC,
            onExit=self.unmount,
            terminalColumns=self.terminalColumns,
            terminalRows=self.terminalRows,
            selection=self.selection,
            onCursorDeclaration=self.setCursorDeclaration,
        )
        self.app.owner = self

    def setSearchHighlight(self, query: str) -> None:
        self.searchHighlightQuery = query

    def setCursorDeclaration(self, declaration: CursorDeclaration | None, clearIfNode: DOMElement | None = None) -> None:
        if declaration is None and clearIfNode is not None and self.cursorDeclaration is not None:
            if self.cursorDeclaration.node is not clearIfNode:
                return
        self.cursorDeclaration = declaration

    def render(self, node: Any) -> None:
        self.currentNode = node
        rendered = self.app.render(node)
        if _should_render_raw_text(rendered):
            text = _coerce_text(rendered)
            self.options.stdout.write(text)
            if hasattr(self.options.stdout, "flush"):
                self.options.stdout.flush()
            return
        self._replace_root_children(rendered)
        self._compute_layout()
        self.onRender()

    def onRender(self) -> None:
        if self.isUnmounted:
            return
        if isinstance(self.currentNode, str) and not self.rootNode.childNodes:
            self.options.stdout.write(self.currentNode)
            if hasattr(self.options.stdout, "flush"):
                self.options.stdout.flush()
            return
        frame = self.renderer({
            "frontFrame": self.frontFrame,
            "backFrame": self.backFrame,
            "isTTY": bool(getattr(self.options.stdout, "isatty", lambda: False)()),
            "terminalWidth": self.terminalColumns,
            "terminalRows": self.terminalRows,
            "altScreen": False,
            "prevFrameContaminated": False,
        })
        diff = self.log.render(self.frontFrame, frame)
        writeDiffToTerminal(self.options.stdout, diff)
        self.frontFrame, self.backFrame = frame, self.frontFrame
        if self.options.onFrame is not None:
            self.options.onFrame(FrameEvent())

    def waitUntilExit(self) -> None:
        wait_fn = self.options.waitUntilExit
        if wait_fn is not None:
            wait_fn()
            return
        self._exit_event.wait()

    def unmount(self, error: Exception | None = None) -> None:
        self.isUnmounted = True
        self.app.cleanup()
        delete_instance(_stdout_fd(self.options.stdout))
        self._exit_event.set()
        if error is not None:
            raise error

    def _replace_root_children(self, rendered: Any) -> None:
        while self.rootNode.childNodes:
            removeChildNode(self.rootNode, self.rootNode.childNodes[0])
        nodes = _coerce_rendered_to_nodes(rendered)
        for child in nodes:
            appendChildNode(self.rootNode, child)

    def _compute_layout(self) -> None:
        if self.rootNode.yogaNode is None:
            return
        self.rootNode.yogaNode.setWidth(self.terminalColumns)
        self.rootNode.yogaNode.calculateLayout(self.terminalColumns)


def _coerce_rendered_to_nodes(rendered: Any) -> list[DOMElement | TextNode]:
    if rendered is None:
        return []
    if isinstance(rendered, (DOMElement, TextNode)):
        return [rendered]
    if isinstance(rendered, (list, tuple)):
        result: list[DOMElement | TextNode] = []
        for item in rendered:
            result.extend(_coerce_rendered_to_nodes(item))
        return result
    if isinstance(rendered, io.StringIO):
        return [createTextNode(rendered.getvalue())]
    return [createTextNode(str(rendered))]


def _should_render_raw_text(rendered: Any) -> bool:
    return isinstance(rendered, (str, bytes, int, float, bool, io.StringIO))


def _coerce_text(rendered: Any) -> str:
    if isinstance(rendered, bytes):
        return rendered.decode()
    if isinstance(rendered, io.StringIO):
        return rendered.getvalue()
    return str(rendered)


def _stdout_fd(stdout: Any) -> int:
    fileno = getattr(stdout, "fileno", None)
    if callable(fileno):
        try:
            return int(fileno())
        except OSError:
            return id(stdout)
    return id(stdout)
