"""App-state access surface — mirrors src/state/AppState.tsx."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Any, Callable, Iterator, Optional

from .AppStateStore import (
    AppState,
    AppStateStore,
    CompletionBoundary,
    IDLE_SPECULATION_STATE,
    SpeculationResult,
    SpeculationState,
    getDefaultAppState,
)
from .onChangeAppState import onChangeAppState
from .store import createStore


AppStoreContext: ContextVar[Optional[AppStateStore]] = ContextVar("AppStoreContext", default=None)
HasAppStateContext: ContextVar[bool] = ContextVar("HasAppStateContext", default=False)


@contextmanager
def AppStateProvider(
    *,
    initialState: Optional[AppState] = None,
    onChangeAppStateCallback: Optional[Callable[[dict[str, AppState]], None]] = None,
) -> Iterator[AppStateStore]:
    if HasAppStateContext.get():
        raise RuntimeError("AppStateProvider can not be nested within another AppStateProvider")

    callback = onChangeAppStateCallback or (lambda change: onChangeAppState(newState=change["newState"], oldState=change["oldState"]))
    store = createStore(initialState if initialState is not None else getDefaultAppState(), callback)
    store_token: Token[Optional[AppStateStore]] = AppStoreContext.set(store)
    has_token: Token[bool] = HasAppStateContext.set(True)
    try:
        yield store
    finally:
        HasAppStateContext.reset(has_token)
        AppStoreContext.reset(store_token)


def useAppStore() -> AppStateStore:
    store = AppStoreContext.get()
    if store is None:
        raise ReferenceError("useAppState/useSetAppState cannot be called outside of an AppStateProvider")
    return store


def useAppState(selector: Callable[[AppState], Any]) -> Any:
    return selector(useAppStore().getState())


def useSetAppState() -> Callable[[Callable[[AppState], AppState]], None]:
    return useAppStore().setState


def useAppStateStore() -> AppStateStore:
    return useAppStore()


def useAppStateMaybeOutsideOfProvider(selector: Callable[[AppState], Any]) -> Any | None:
    store = AppStoreContext.get()
    if store is None:
        return None
    return selector(store.getState())


__all__ = [
    "AppState",
    "AppStateStore",
    "CompletionBoundary",
    "IDLE_SPECULATION_STATE",
    "SpeculationResult",
    "SpeculationState",
    "getDefaultAppState",
    "AppStoreContext",
    "HasAppStateContext",
    "AppStateProvider",
    "useAppStore",
    "useAppState",
    "useSetAppState",
    "useAppStateStore",
    "useAppStateMaybeOutsideOfProvider",
]