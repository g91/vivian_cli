"""Port of src/utils/settings/changeDetector.ts"""
from __future__ import annotations
import os
import threading
import time
from typing import Optional, Callable, Dict, Any, List

_watchers: List[threading.Thread] = []
_stop_events: List[threading.Event] = []


def createSettingsFileWatcher(
    path: str,
    on_change: Callable[[str], None],
    poll_interval_ms: int = 2000,
) -> Callable[[], None]:
    """Create a polling-based file watcher. Returns a dispose function."""
    stop_event = threading.Event()
    _stop_events.append(stop_event)

    def _watch() -> None:
        last_mtime: Optional[float] = None
        try:
            last_mtime = os.path.getmtime(path) if os.path.isfile(path) else None
        except OSError:
            last_mtime = None

        while not stop_event.is_set():
            stop_event.wait(poll_interval_ms / 1000.0)
            try:
                current_mtime = os.path.getmtime(path) if os.path.isfile(path) else None
            except OSError:
                current_mtime = None
            if current_mtime != last_mtime:
                last_mtime = current_mtime
                try:
                    on_change(path)
                except Exception:
                    pass

    t = threading.Thread(target=_watch, daemon=True, name=f'settings-watcher-{os.path.basename(path)}')
    _watchers.append(t)
    t.start()

    def dispose() -> None:
        stop_event.set()

    return dispose


def watchSettingsFiles(
    on_change: Callable[[str, str], None],
    sources: Optional[List[str]] = None,
) -> Callable[[], None]:
    """Watch all settings files and call on_change(source, path) when any changes."""
    if sources is None:
        sources = ['userSettings', 'projectSettings', 'localSettings']
    from .settings import getSettingsFilePathForSource
    from .settingsCache import resetSettingsCache

    dispose_fns = []
    for source in sources:
        path = getSettingsFilePathForSource(source)
        if path is None:
            continue

        def make_handler(src: str, pth: str) -> Callable[[str], None]:
            def handler(changed_path: str) -> None:
                from .internalWrites import consumeInternalWrite
                if consumeInternalWrite(pth, 2000):
                    return  # Our own write, skip
                resetSettingsCache()
                on_change(src, pth)
            return handler

        dispose_fns.append(createSettingsFileWatcher(path, make_handler(source, path)))

    def dispose_all() -> None:
        for fn in dispose_fns:
            fn()

    return dispose_all


def stopAllSettingsWatchers() -> None:
    """Stop all active settings file watchers."""
    for event in _stop_events:
        event.set()
    _stop_events.clear()
    _watchers.clear()
