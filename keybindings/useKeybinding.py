"""Keybinding hooks — mirrors src/keybindings/useKeybinding.ts."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .KeybindingContext import HandlerRegistration, useOptionalKeybindingContext


@dataclass
class Options:
    context: str = "Global"
    isActive: bool = True


def _coerce_options(options: Options | dict[str, Any] | None) -> Options:
    if isinstance(options, Options):
        return options
    if isinstance(options, dict):
        return Options(
            context=str(options.get("context", "Global")),
            isActive=bool(options.get("isActive", True)),
        )
    return Options()


def useKeybinding(
    action: str,
    handler: Callable[[], object],
    options: Options | dict[str, Any] | None = None,
) -> Callable[[], None]:
    resolved_options = _coerce_options(options)
    keybindingContext = useOptionalKeybindingContext()
    if keybindingContext is None or not resolved_options.isActive:
        return lambda: None
    return keybindingContext.registerHandler(
        HandlerRegistration(
            action=action,
            context=resolved_options.context,
            handler=handler,
        )
    )


def useKeybindings(
    handlers: dict[str, Callable[[], object]],
    options: Options | dict[str, Any] | None = None,
) -> Callable[[], None]:
    resolved_options = _coerce_options(options)
    keybindingContext = useOptionalKeybindingContext()
    if keybindingContext is None or not resolved_options.isActive:
        return lambda: None

    unregister_fns: list[Callable[[], None]] = []
    for action, handler in handlers.items():
        unregister_fns.append(
            keybindingContext.registerHandler(
                HandlerRegistration(
                    action=action,
                    context=resolved_options.context,
                    handler=handler,
                )
            )
        )

    def unregister_all() -> None:
        for unregister in unregister_fns:
            unregister()

    return unregister_all


__all__ = ["Options", "useKeybinding", "useKeybindings"]