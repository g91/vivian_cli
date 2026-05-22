"""Generic state store — mirrors src/state/store.ts."""
from __future__ import annotations

from typing import Callable, Generic, Optional, TypeVar

T = TypeVar("T")

Listener = Callable[[], None]


class Store(Generic[T]):
    """Generic reactive store.

    Mirrors the Store<T> type from store.ts.
    """

    def __init__(
        self,
        state: T,
        on_change: Optional[Callable[[dict], None]] = None,
    ) -> None:
        self._state: T = state
        self._listeners: set[Listener] = set()
        self._on_change = on_change

    def get_state(self) -> T:
        return self._state

    def getState(self) -> T:
        return self.get_state()

    def set_state(self, updater: Callable[[T], T]) -> None:
        prev = self._state
        next_state = updater(prev)
        if next_state is prev:
            return
        self._state = next_state
        if self._on_change is not None:
            self._on_change({"newState": next_state, "oldState": prev})
        for listener in list(self._listeners):
            listener()

    def setState(self, updater: Callable[[T], T]) -> None:
        self.set_state(updater)

    def subscribe(self, listener: Listener) -> Callable[[], None]:
        self._listeners.add(listener)

        def unsubscribe() -> None:
            self._listeners.discard(listener)

        return unsubscribe

    subscribe_listener = subscribe


def create_store(initial_state: T, on_change: Optional[Callable[[dict], None]] = None) -> Store[T]:
    """Create a new Store — mirrors createStore() from store.ts."""
    return Store(initial_state, on_change)


def createStore(initial_state: T, on_change: Optional[Callable[[dict], None]] = None) -> Store[T]:
    return create_store(initial_state, on_change)


def StateStore() -> "Store[dict]":
    """Create an AppState store pre-seeded with default app state.

    Convenience alias used by VivianCLI and QueryEngine.
    """
    from .AppStateStore import get_default_app_state
    from .onChangeAppState import onChangeAppState

    return Store(
        get_default_app_state(),
        lambda change: onChangeAppState(
            newState=change["newState"],
            oldState=change["oldState"],
        ),
    )

