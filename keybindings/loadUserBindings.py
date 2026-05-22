"""User keybinding loader with hot-reload support — mirrors src/keybindings/loadUserBindings.ts."""
from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

from ..services.analytics.growthbook import getFeatureValue_CACHED_MAY_BE_STALE
from ..services.analytics.index import logEvent
from ..utils.debug import log_for_debugging
from ..utils.errors import error_message, is_enoent
from ..utils.settings.changeDetector import createSettingsFileWatcher
from ..utils.signal import create_signal
from ..utils.slowOperations import json_parse
from .defaultBindings import DEFAULT_BINDINGS
from .parser import KeybindingBlock, ParsedBinding, parseBindings
from .validate import (
    KeybindingWarning,
    checkDuplicateKeysInJson,
    isKeybindingBlockArray,
    validateBindings,
)


FILE_STABILITY_THRESHOLD_MS = 500
FILE_STABILITY_POLL_INTERVAL_MS = 200


KeybindingsLoadResult = dict[str, list[Any]]

_watcher_dispose: Any = None
_initialized = False
_disposed = False
_cached_bindings: list[ParsedBinding] | None = None
_cached_warnings: list[KeybindingWarning] = []
_keybindings_changed = create_signal()
_last_custom_bindings_log_date: str | None = None


def isKeybindingCustomizationEnabled() -> bool:
    return bool(
        getFeatureValue_CACHED_MAY_BE_STALE(
            "tengu_keybinding_customization_release",
            False,
        )
    )


def getKeybindingsPath() -> str:
    return str(Path.home() / ".vivian" / "keybindings.json")


def getDefaultParsedBindings() -> list[ParsedBinding]:
    return parseBindings(DEFAULT_BINDINGS)


def logCustomBindingsLoadedOncePerDay(userBindingCount: int) -> None:
    global _last_custom_bindings_log_date
    today = __import__("datetime").datetime.now().date().isoformat()
    if _last_custom_bindings_log_date == today:
        return
    _last_custom_bindings_log_date = today
    logEvent(
        "tengu_custom_keybindings_loaded",
        {"user_binding_count": userBindingCount},
    )


def _parse_user_blocks(parsed: Any, default_bindings: list[ParsedBinding]) -> tuple[list[KeybindingBlock] | None, list[KeybindingWarning]]:
    if not isinstance(parsed, dict) or "bindings" not in parsed:
        return None, [
            {
                "type": "parse_error",
                "severity": "error",
                "message": 'keybindings.json must have a "bindings" array',
                "suggestion": 'Use format: { "bindings": [ ... ] }',
            }
        ]

    user_blocks = parsed.get("bindings")
    if not isKeybindingBlockArray(user_blocks):
        error_msg = (
            '"bindings" must be an array'
            if not isinstance(user_blocks, list)
            else "keybindings.json contains invalid block structure"
        )
        suggestion = (
            'Set "bindings" to an array of keybinding blocks'
            if not isinstance(user_blocks, list)
            else 'Each block must have "context" (string) and "bindings" (object)'
        )
        return None, [
            {
                "type": "parse_error",
                "severity": "error",
                "message": error_msg,
                "suggestion": suggestion,
            }
        ]

    coerced_blocks = [
        KeybindingBlock(context=item["context"], bindings=dict(item["bindings"]))
        for item in user_blocks
    ]
    return coerced_blocks, []


def _load_keybindings_impl() -> KeybindingsLoadResult:
    default_bindings = getDefaultParsedBindings()
    if not isKeybindingCustomizationEnabled():
        return {"bindings": default_bindings, "warnings": []}

    user_path = getKeybindingsPath()
    try:
        with open(user_path, "r", encoding="utf-8") as handle:
            content = handle.read()
        parsed = json_parse(content)
        user_blocks, early_warnings = _parse_user_blocks(parsed, default_bindings)
        if user_blocks is None:
            log_for_debugging(f"[keybindings] Invalid keybindings.json: {early_warnings[0]['message']}")
            return {"bindings": default_bindings, "warnings": early_warnings}

        user_parsed = parseBindings(user_blocks)
        log_for_debugging(
            f"[keybindings] Loaded {len(user_parsed)} user bindings from {user_path}"
        )
        merged_bindings = [*default_bindings, *user_parsed]
        logCustomBindingsLoadedOncePerDay(len(user_parsed))

        duplicate_key_warnings = checkDuplicateKeysInJson(content)
        warnings = [
            *duplicate_key_warnings,
            *validateBindings(
                [
                    {"context": block.context, "bindings": block.bindings}
                    for block in user_blocks
                ],
                merged_bindings,
            ),
        ]
        if warnings:
            log_for_debugging(
                f"[keybindings] Found {len(warnings)} validation issue(s)"
            )
        return {"bindings": merged_bindings, "warnings": warnings}
    except Exception as exc:
        if is_enoent(exc):
            return {"bindings": default_bindings, "warnings": []}
        log_for_debugging(
            f"[keybindings] Error loading {user_path}: {error_message(exc)}"
        )
        return {
            "bindings": default_bindings,
            "warnings": [
                {
                    "type": "parse_error",
                    "severity": "error",
                    "message": f"Failed to parse keybindings.json: {error_message(exc)}",
                }
            ],
        }


async def loadKeybindings() -> KeybindingsLoadResult:
    return _load_keybindings_impl()


def loadKeybindingsSync() -> list[ParsedBinding]:
    global _cached_bindings
    if _cached_bindings is not None:
        return _cached_bindings
    result = loadKeybindingsSyncWithWarnings()
    return result["bindings"]


def loadKeybindingsSyncWithWarnings() -> KeybindingsLoadResult:
    global _cached_bindings, _cached_warnings
    if _cached_bindings is not None:
        return {"bindings": _cached_bindings, "warnings": _cached_warnings}

    result = _load_keybindings_impl()
    _cached_bindings = result["bindings"]
    _cached_warnings = result["warnings"]
    return result


async def initializeKeybindingWatcher() -> None:
    global _initialized, _watcher_dispose
    if _initialized or _disposed:
        return
    if not isKeybindingCustomizationEnabled():
        log_for_debugging(
            "[keybindings] Skipping file watcher - user customization disabled"
        )
        return

    user_path = getKeybindingsPath()
    watch_dir = os.path.dirname(user_path)
    if not os.path.isdir(watch_dir):
        log_for_debugging(f"[keybindings] Not watching: {watch_dir} does not exist")
        return

    _initialized = True
    log_for_debugging(f"[keybindings] Watching for changes to {user_path}")

    def _handle_change(path: str) -> None:
        handleChange(path)

    _watcher_dispose = createSettingsFileWatcher(
        user_path,
        _handle_change,
        poll_interval_ms=FILE_STABILITY_POLL_INTERVAL_MS,
    )


def disposeKeybindingWatcher() -> None:
    global _watcher_dispose, _disposed
    _disposed = True
    if _watcher_dispose is not None:
        _watcher_dispose()
        _watcher_dispose = None
    _keybindings_changed.clear()


subscribeToKeybindingChanges = _keybindings_changed.subscribe


def handleChange(path: str) -> None:
    global _cached_bindings, _cached_warnings
    log_for_debugging(f"[keybindings] Detected change to {path}")
    try:
        result = _load_keybindings_impl()
        _cached_bindings = result["bindings"]
        _cached_warnings = result["warnings"]
        _keybindings_changed.emit(result)
    except Exception as exc:
        log_for_debugging(f"[keybindings] Error reloading: {error_message(exc)}")


def handleDelete(path: str) -> None:
    global _cached_bindings, _cached_warnings
    log_for_debugging(f"[keybindings] Detected deletion of {path}")
    default_bindings = getDefaultParsedBindings()
    _cached_bindings = default_bindings
    _cached_warnings = []
    _keybindings_changed.emit({"bindings": default_bindings, "warnings": []})


def getCachedKeybindingWarnings() -> list[KeybindingWarning]:
    return _cached_warnings


def resetKeybindingLoaderForTesting() -> None:
    global _initialized, _disposed, _cached_bindings, _cached_warnings
    global _last_custom_bindings_log_date, _watcher_dispose
    _initialized = False
    _disposed = False
    _cached_bindings = None
    _cached_warnings = []
    _last_custom_bindings_log_date = None
    if _watcher_dispose is not None:
        _watcher_dispose()
        _watcher_dispose = None
    _keybindings_changed.clear()


is_keybinding_customization_enabled = isKeybindingCustomizationEnabled
get_keybindings_path = getKeybindingsPath
get_default_parsed_bindings = getDefaultParsedBindings
log_custom_bindings_loaded_once_per_day = logCustomBindingsLoadedOncePerDay
load_keybindings = loadKeybindings
load_keybindings_sync = loadKeybindingsSync
load_keybindings_sync_with_warnings = loadKeybindingsSyncWithWarnings
initialize_keybinding_watcher = initializeKeybindingWatcher
dispose_keybinding_watcher = disposeKeybindingWatcher
subscribe_to_keybinding_changes = subscribeToKeybindingChanges
handle_change = handleChange
handle_delete = handleDelete
get_cached_keybinding_warnings = getCachedKeybindingWarnings
reset_keybinding_loader_for_testing = resetKeybindingLoaderForTesting