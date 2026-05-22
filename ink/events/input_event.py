"""Port of src/ink/events/input-event.ts."""
from .event import Event


class InputEvent(Event):
    __slots__ = ("key", "input")

    def __init__(self, key: str, input: str) -> None:
        super().__init__("input")
        self.key = key
        self.input = input
