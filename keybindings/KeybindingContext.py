"""Keybinding context — mirrors src/keybindings/KeybindingContext.tsx."""
from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Callable, Optional

from .parser import ParsedBinding, ParsedKeystroke
from .resolver import getBindingDisplayText, resolveKeyWithChordState
from .types import ChordResolveResult, KeybindingContextName


@dataclass(frozen=True)
class HandlerRegistration:
    action: str
    context: KeybindingContextName
    handler: Callable[[], object]


class KeybindingContextValue:
    """Singleton-style context container for keybinding resolution and handlers."""

    def __init__(self, bindings: Optional[list[ParsedBinding]] = None) -> None:
        self._lock = RLock()
        self.bindings: list[ParsedBinding] = list(bindings or [])
        self.pendingChord: list[ParsedKeystroke] | None = None
        self.activeContexts: set[KeybindingContextName] = set()
        self._handler_registry: dict[str, list[HandlerRegistration]] = {}

    def updateBindings(self, bindings: list[ParsedBinding]) -> None:
        with self._lock:
            self.bindings = list(bindings)

    def resolve(
        self,
        input_value: str,
        key: dict,
        activeContexts: list[KeybindingContextName],
    ) -> ChordResolveResult:
        return resolveKeyWithChordState(
            input_value,
            key,
            list(activeContexts),
            self.bindings,
            self.pendingChord,
        )

    def setPendingChord(self, pending: list[ParsedKeystroke] | None) -> None:
        with self._lock:
            self.pendingChord = list(pending) if pending is not None else None

    def getDisplayText(self, action: str, context: KeybindingContextName) -> str | None:
        return getBindingDisplayText(action, context, self.bindings)

    def registerActiveContext(self, context: KeybindingContextName) -> None:
        with self._lock:
            self.activeContexts.add(context)

    def unregisterActiveContext(self, context: KeybindingContextName) -> None:
        with self._lock:
            self.activeContexts.discard(context)

    def registerHandler(self, registration: HandlerRegistration) -> Callable[[], None]:
        with self._lock:
            handlers = self._handler_registry.setdefault(registration.action, [])
            handlers.append(registration)

        def unregister() -> None:
            with self._lock:
                handlers = self._handler_registry.get(registration.action)
                if not handlers:
                    return
                self._handler_registry[registration.action] = [
                    existing for existing in handlers if existing != registration
                ]
                if not self._handler_registry[registration.action]:
                    self._handler_registry.pop(registration.action, None)

        return unregister

    def invokeAction(self, action: str) -> bool:
        with self._lock:
            handlers = list(self._handler_registry.get(action, []))
            active_contexts = set(self.activeContexts)
        for registration in handlers:
            if registration.context in active_contexts:
                registration.handler()
                return True
        return False

    def getHandlerContexts(self) -> list[KeybindingContextName]:
        with self._lock:
            seen: set[KeybindingContextName] = set()
            ordered: list[KeybindingContextName] = []
            for handlers in self._handler_registry.values():
                for registration in handlers:
                    if registration.context in seen:
                        continue
                    seen.add(registration.context)
                    ordered.append(registration.context)
            return ordered

    def getHandlersForAction(self, action: str) -> list[HandlerRegistration]:
        with self._lock:
            return list(self._handler_registry.get(action, []))


_keybinding_context_instance: KeybindingContextValue | None = None


def KeybindingProvider(
    bindings: list[ParsedBinding],
    pendingChordRef: object | None = None,
    pendingChord: list[ParsedKeystroke] | None = None,
    setPendingChord: Callable[[list[ParsedKeystroke] | None], None] | None = None,
    activeContexts: set[KeybindingContextName] | None = None,
    registerActiveContext: Callable[[KeybindingContextName], None] | None = None,
    unregisterActiveContext: Callable[[KeybindingContextName], None] | None = None,
    handlerRegistryRef: object | None = None,
    children: object | None = None,
) -> KeybindingContextValue:
    del pendingChordRef, setPendingChord, registerActiveContext, unregisterActiveContext, handlerRegistryRef, children

    global _keybinding_context_instance
    if _keybinding_context_instance is None:
        _keybinding_context_instance = KeybindingContextValue(bindings)
    else:
        _keybinding_context_instance.updateBindings(bindings)
    if pendingChord is not None:
        _keybinding_context_instance.setPendingChord(pendingChord)
    if activeContexts is not None:
        _keybinding_context_instance.activeContexts = set(activeContexts)
    return _keybinding_context_instance


def useKeybindingContext() -> KeybindingContextValue:
    ctx = useOptionalKeybindingContext()
    if ctx is None:
        raise RuntimeError("useKeybindingContext must be used within KeybindingProvider")
    return ctx


def useOptionalKeybindingContext() -> KeybindingContextValue | None:
    return _keybinding_context_instance


def useRegisterKeybindingContext(
    context: KeybindingContextName,
    isActive: bool = True,
) -> Callable[[], None]:
    keybindingContext = useOptionalKeybindingContext()
    if keybindingContext is None or not isActive:
        return lambda: None
    keybindingContext.registerActiveContext(context)

    def unregister() -> None:
        keybindingContext.unregisterActiveContext(context)

    return unregister


__all__ = [
    "HandlerRegistration",
    "KeybindingContextValue",
    "KeybindingProvider",
    "useKeybindingContext",
    "useOptionalKeybindingContext",
    "useRegisterKeybindingContext",
]