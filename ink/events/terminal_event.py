"""Port of src/ink/events/terminal-event.ts."""
from .event import Event


class TerminalEvent(Event):
    __slots__ = ("data",)

    def __init__(self, data: str) -> None:
        super().__init__("terminal")
        self.data = data
