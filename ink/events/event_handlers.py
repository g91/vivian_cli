"""Port of src/ink/events/event-handlers.ts."""
from __future__ import annotations

from typing import Any, Callable

from .click_event import ClickEvent

EVENT_HANDLER_PROPS = {
    "onClick", "onMouseEnter", "onMouseLeave",
    "onFocus", "onBlur", "onInput", "onKeyDown", "onKeyUp",
}

EventHandlerProps = dict[str, Callable[..., Any]]
