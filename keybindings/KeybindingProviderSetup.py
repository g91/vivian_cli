"""Keybinding provider setup — mirrors src/keybindings/KeybindingProviderSetup.tsx."""
from __future__ import annotations

import asyncio
import logging
import threading
from typing import Any, Callable

from ..context.notifications import useNotifications
from ..utils.stringUtils import plural
from .KeybindingContext import KeybindingProvider, useKeybindingContext
from .loadUserBindings import (
    initializeKeybindingWatcher,
    loadKeybindingsSyncWithWarnings,
    subscribeToKeybindingChanges,
)
from .resolver import resolveKeyWithChordState

logger = logging.getLogger(__name__)

CHORD_TIMEOUT_MS = 1000

_setup_unsubscribe: Callable[[], None] | None = None
_chord_timeout: threading.Timer | None = None


def _stop_immediate_propagation(event: object | None) -> None:
    if event is None:
        return
    stop = getattr(event, "stopImmediatePropagation", None)
    if callable(stop):
        stop()


def _clear_chord_timeout() -> None:
    global _chord_timeout
    if _chord_timeout is not None:
        _chord_timeout.cancel()
        _chord_timeout = None


def _initialize_watcher() -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(initializeKeybindingWatcher())
        return
    loop.create_task(initializeKeybindingWatcher())


def _set_pending_chord(pending: list | None) -> None:
    global _chord_timeout
    context = useKeybindingContext()
    _clear_chord_timeout()
    context.setPendingChord(pending)
    if pending is None:
        return

    def cancel_pending() -> None:
        logger.debug("[keybindings] Chord timeout - cancelling")
        context.setPendingChord(None)

    _chord_timeout = threading.Timer(CHORD_TIMEOUT_MS / 1000.0, cancel_pending)
    _chord_timeout.daemon = True
    _chord_timeout.start()


def useKeybindingWarnings(warnings: list[dict], isReload: bool) -> None:
    del isReload
    notifications = useNotifications()
    notification_key = "keybinding-config-warning"
    if not warnings:
        notifications.removeNotification(notification_key)
        return

    error_count = sum(1 for warning in warnings if warning.get("severity") == "error")
    warn_count = sum(1 for warning in warnings if warning.get("severity") == "warning")
    if error_count > 0 and warn_count > 0:
        message = (
            f"Found {error_count} keybinding {plural(error_count, 'error')} "
            f"and {warn_count} {plural(warn_count, 'warning')}"
        )
    elif error_count > 0:
        message = f"Found {error_count} keybinding {plural(error_count, 'error')}"
    else:
        message = f"Found {warn_count} keybinding {plural(warn_count, 'warning')}"
    notifications.addNotification(
        {
            "key": notification_key,
            "text": f"{message} · /doctor for details",
            "color": "error" if error_count > 0 else "warning",
            "priority": "immediate" if error_count > 0 else "high",
            "timeoutMs": 60000,
        }
    )


def KeybindingSetup(children: object | None = None):
    del children
    global _setup_unsubscribe

    result = loadKeybindingsSyncWithWarnings()
    logger.debug(
        "[keybindings] KeybindingSetup initialized with %s bindings, %s warnings",
        len(result["bindings"]),
        len(result["warnings"]),
    )
    context = KeybindingProvider(bindings=result["bindings"])
    useKeybindingWarnings(result["warnings"], False)

    _initialize_watcher()
    if _setup_unsubscribe is None:
        def _handle_reload(reload_result: dict[str, Any]) -> None:
            logger.debug(
                "[keybindings] Reloaded: %s bindings, %s warnings",
                len(reload_result["bindings"]),
                len(reload_result["warnings"]),
            )
            context.updateBindings(reload_result["bindings"])
            useKeybindingWarnings(reload_result["warnings"], True)

        _setup_unsubscribe = subscribeToKeybindingChanges(_handle_reload)

    return context


def disposeKeybindingSetup() -> None:
    global _setup_unsubscribe
    if _setup_unsubscribe is not None:
        _setup_unsubscribe()
        _setup_unsubscribe = None
    _clear_chord_timeout()


def ChordInterceptor(input_value: str, key: dict[str, Any], event: object | None = None) -> dict[str, Any]:
    context = useKeybindingContext()
    active_contexts = [*context.getHandlerContexts(), *context.activeContexts, "Global"]
    deduped_contexts: list[str] = []
    seen: set[str] = set()
    for item in active_contexts:
        if item in seen:
            continue
        seen.add(item)
        deduped_contexts.append(item)

    was_in_chord = context.pendingChord is not None
    result = resolveKeyWithChordState(
        input_value,
        key,
        deduped_contexts,
        context.bindings,
        context.pendingChord,
    )
    if result["type"] == "chord_started":
        _set_pending_chord(result["pending"])
        _stop_immediate_propagation(event)
    elif result["type"] == "match":
        _set_pending_chord(None)
        if was_in_chord:
            for registration in context.getHandlersForAction(result["action"]):
                if registration.context in seen:
                    registration.handler()
                    _stop_immediate_propagation(event)
                    break
    elif result["type"] in {"chord_cancelled", "unbound"}:
        _set_pending_chord(None)
        _stop_immediate_propagation(event)
    return result


__all__ = [
    "CHORD_TIMEOUT_MS",
    "ChordInterceptor",
    "KeybindingSetup",
    "disposeKeybindingSetup",
    "useKeybindingWarnings",
]