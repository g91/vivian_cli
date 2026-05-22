"""Port of src/ink/hooks/use-input.ts."""
from __future__ import annotations

from typing import Any, Callable

from ..components.StdinContext import getStdinContext


def useInput(
    inputHandler: Callable[[str, dict[str, Any]], None],
    options: dict[str, Any] | None = None,
) -> Callable[[], None]:
    """Register an input handler against the current Ink stdin context."""
    options = options or {}
    context = getStdinContext()
    if options.get("isActive", True) is False:
        return lambda: None
    if context.internal_eventEmitter is None:
        return lambda: None

    context.setRawMode(True)

    def listener(event: Any) -> None:
        key = event.key if isinstance(getattr(event, "key", None), dict) else {"name": getattr(event, "key", None)}
        inputHandler(getattr(event, "input", ""), key)

    context.internal_eventEmitter.on("input", listener)

    def dispose() -> None:
        context.internal_eventEmitter.off("input", listener)
        context.setRawMode(False)

    return dispose


use_input = useInput
