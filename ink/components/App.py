"""Port of src/ink/components/App.tsx."""
from __future__ import annotations

import sys
import threading
import time
from contextlib import ExitStack
from typing import Any, Callable, TextIO

from ..events.emitter import Emitter
from ..events.input_event import InputEvent
from ..parse_keypress import parseMultipleKeypresses, INITIAL_STATE
from ..selection import SelectionState
from ..terminal_querier import TerminalQuerier
from .AppContext import AppContextProps, provideAppContext
from .ClockContext import ClockProvider, SharedClock
from .CursorDeclarationContext import CursorDeclaration, provideCursorDeclarationContext
from .ErrorOverview import renderErrorOverview
from .StdinContext import StdinContextProps, provideStdinContext
from .TerminalFocusContext import TerminalFocusProvider
from .TerminalSizeContext import TerminalSize, provideTerminalSizeContext


class App:
    """Runtime holder for Ink-like input, timer, and context state."""

    def __init__(
        self,
        *,
        stdin: TextIO,
        stdout: TextIO,
        stderr: TextIO,
        exitOnCtrlC: bool,
        onExit: Callable[[Exception | None], None],
        terminalColumns: int,
        terminalRows: int,
        selection: SelectionState | None = None,
        onSelectionChange: Callable[[], None] | None = None,
        onCursorDeclaration: Callable[[CursorDeclaration | None, Any | None], None] | None = None,
    ) -> None:
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.exitOnCtrlC = exitOnCtrlC
        self.onExit = onExit
        self.terminalColumns = terminalColumns
        self.terminalRows = terminalRows
        self.selection = selection
        self.onSelectionChange = onSelectionChange or (lambda: None)
        self.onCursorDeclaration = onCursorDeclaration or (lambda declaration, clear_if_node=None: None)
        self.internal_eventEmitter = Emitter()
        self.keyParseState = INITIAL_STATE
        self.querier = TerminalQuerier(stdout)
        self.clock = SharedClock()
        self._raw_mode_enabled = False
        self._timer_threads: list[tuple[threading.Event, threading.Thread]] = []
        self._last_error: Exception | None = None

    def isRawModeSupported(self) -> bool:
        return bool(getattr(self.stdin, "isatty", lambda: False)())

    def handleSetRawMode(self, isEnabled: bool) -> None:
        if not self.isRawModeSupported():
            return
        set_raw_mode = getattr(self.stdin, "setraw", None)
        if callable(set_raw_mode):
            set_raw_mode(isEnabled)
        elif hasattr(self.stdin, "setRawMode"):
            self.stdin.setRawMode(isEnabled)
        self._raw_mode_enabled = isEnabled

    def handleExit(self, error: Exception | None = None) -> None:
        self._last_error = error
        self.onExit(error)

    def registerInputHandler(self, handler: Callable[[str, dict[str, Any], InputEvent], None]) -> Callable[[], None]:
        def listener(event: InputEvent) -> None:
            key_payload = event.key if isinstance(event.key, dict) else {"name": event.key}
            handler(event.input, key_payload, event)

        self.internal_eventEmitter.on("input", listener)

        def unregister() -> None:
            self.internal_eventEmitter.off("input", listener)

        return unregister

    def registerStdinHandler(self, handler: Callable[[str], None]) -> Callable[[], None]:
        def listener(event: InputEvent) -> None:
            handler(event.input)

        self.internal_eventEmitter.on("input", listener)

        def unregister() -> None:
            self.internal_eventEmitter.off("input", listener)

        return unregister

    def emitInput(self, data: str) -> None:
        if not data:
            return
        keys, self.keyParseState = parseMultipleKeypresses(self.keyParseState, data)
        for parsed in keys:
            key_payload = parsed.get("key", {}) if isinstance(parsed, dict) else {}
            input_value = parsed.get("input", "") if isinstance(parsed, dict) else str(parsed)
            event = InputEvent(key=key_payload, input=input_value)
            self.internal_eventEmitter.emit("input", event)
            if input_value == "c" and key_payload.get("ctrl") and self.exitOnCtrlC:
                self.handleExit(None)

    def registerInterval(self, callback: Callable[[], None], intervalMs: int, *, repeat: bool = True) -> Callable[[], None]:
        stop_event = threading.Event()

        def runner() -> None:
            if not repeat:
                if not stop_event.wait(intervalMs / 1000):
                    callback()
                return
            while not stop_event.wait(intervalMs / 1000):
                callback()

        thread = threading.Thread(target=runner, daemon=True)
        thread.start()
        self._timer_threads.append((stop_event, thread))

        def cancel() -> None:
            stop_event.set()

        return cancel

    def setSearchHighlight(self, query: str) -> None:
        owner = getattr(self, "owner", None)
        if owner is not None:
            owner.setSearchHighlight(query)

    def render(self, node: Any) -> Any:
        with ExitStack() as stack:
            stack.enter_context(provideTerminalSizeContext(TerminalSize(columns=self.terminalColumns, rows=self.terminalRows)))
            stack.enter_context(provideAppContext(AppContextProps(exit=self.handleExit)))
            stack.enter_context(provideStdinContext(StdinContextProps(
                stdin=self.stdin,
                setRawMode=self.handleSetRawMode,
                isRawModeSupported=self.isRawModeSupported(),
                internal_exitOnCtrlC=self.exitOnCtrlC,
                app=self,
                internal_eventEmitter=self.internal_eventEmitter,
                internal_querier=self.querier,
            )))
            stack.enter_context(TerminalFocusProvider())
            stack.enter_context(ClockProvider(self.clock))
            stack.enter_context(provideCursorDeclarationContext(self.onCursorDeclaration))
            try:
                if callable(node):
                    return node()
                return node
            except Exception as error:  # pragma: no cover - defensive runtime surface
                self._last_error = error
                self.stderr.write(renderErrorOverview(error) + "\n")
                raise

    def cleanup(self) -> None:
        for stop_event, _thread in self._timer_threads:
            stop_event.set()
        self._timer_threads.clear()
        if self._raw_mode_enabled:
            self.handleSetRawMode(False)
