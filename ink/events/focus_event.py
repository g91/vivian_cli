"""Port of src/ink/events/focus-event.ts."""
from .event import Event


class FocusEvent(Event):
    __slots__ = ("relatedTarget",)

    def __init__(self, type: str, relatedTarget: object | None = None) -> None:
        super().__init__(type)
        self.relatedTarget = relatedTarget
