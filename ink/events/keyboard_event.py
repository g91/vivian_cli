"""Port of src/ink/events/keyboard-event.ts."""
from .event import Event


class KeyboardEvent(Event):
    __slots__ = ("key", "ctrl", "meta", "shift", "alt")

    def __init__(self, key: str, ctrl: bool = False, meta: bool = False, shift: bool = False, alt: bool = False) -> None:
        super().__init__("keyboard")
        self.key = key
        self.ctrl = ctrl
        self.meta = meta
        self.shift = shift
        self.alt = alt
