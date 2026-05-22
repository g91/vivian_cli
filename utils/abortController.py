"""AbortController utilities — mirrors src/utils/abortController.ts"""
from __future__ import annotations

import threading
from typing import Optional, Callable


class AbortSignal:
    """A simple abort signal that can notify listeners when aborted."""

    def __init__(self) -> None:
        self.aborted = False
        self.reason: object = None
        self._listeners: list[Callable] = []
        self._lock = threading.Lock()

    def add_event_listener(self, event: str, callback: Callable, *, once: bool = False) -> None:
        if event != "abort":
            return
        if self.aborted:
            callback()
            return
        with self._lock:
            if once:
                def _once_wrapper():
                    callback()
                    self.remove_event_listener(event, _once_wrapper)
                self._listeners.append(_once_wrapper)
            else:
                self._listeners.append(callback)

    def remove_event_listener(self, event: str, callback: Callable) -> None:
        if event != "abort":
            return
        with self._lock:
            try:
                self._listeners.remove(callback)
            except ValueError:
                pass

    def _fire(self, reason: object = None) -> None:
        with self._lock:
            if self.aborted:
                return
            self.aborted = True
            self.reason = reason
            listeners = list(self._listeners)
            self._listeners.clear()
        for cb in listeners:
            try:
                cb()
            except Exception:
                pass


class AbortController:
    """Abort controller — mirrors the web AbortController API."""

    def __init__(self) -> None:
        self.signal = AbortSignal()

    def abort(self, reason: object = None) -> None:
        """Abort all operations associated with this controller."""
        self.signal._fire(reason)


def create_abort_controller(max_listeners: int = 50) -> AbortController:
    """Create an AbortController (max_listeners is no-op in Python)."""
    return AbortController()


def create_child_abort_controller(
    parent: AbortController,
    max_listeners: int = 50,
) -> AbortController:
    """Create a child controller that aborts when the parent aborts."""
    child = create_abort_controller(max_listeners)
    if parent.signal.aborted:
        child.abort(parent.signal.reason)
        return child

    def _propagate():
        child.abort(parent.signal.reason)

    parent.signal.add_event_listener("abort", _propagate, once=True)

    def _cleanup():
        parent.signal.remove_event_listener("abort", _propagate)

    child.signal.add_event_listener("abort", _cleanup, once=True)
    return child
