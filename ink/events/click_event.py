"""Port of src/ink/events/click-event.ts."""
from .event import Event


class ClickEvent(Event):
    __slots__ = ("col", "row", "cellIsBlank", "localCol", "localRow")

    def __init__(self, col: int, row: int, cellIsBlank: bool = False) -> None:
        super().__init__("click")
        self.col = col
        self.row = row
        self.cellIsBlank = cellIsBlank
        self.localCol = 0
        self.localRow = 0
