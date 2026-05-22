"""Port of src/ink/events/terminal-focus-event.ts."""
from .event import Event


class TerminalFocusEvent(Event):
    __slots__ = ("focused",)

    def __init__(self, focused: bool) -> None:
        super().__init__("terminalFocus")
        self.focused = focused
