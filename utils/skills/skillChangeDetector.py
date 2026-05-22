"""Port of src/utils/skillChangeDetector.ts - Watch skill dirs for changes."""
from __future__ import annotations
from typing import Any, Optional, Dict, List, Callable
import os
import asyncio
import logging
import threading
import time

logger = logging.getLogger(__name__)

_DEBOUNCE_SECONDS = 0.3

_watcher: Any = None
_subscribers: List[Callable[[str], None]] = []
_debounce_timer: Optional[threading.Timer] = None
_pending_change_path: Optional[str] = None
_initialized = False


class _SkillsChangedSignal:
    def __init__(self) -> None:
        self._subs: List[Callable] = []

    def subscribe(self, fn: Callable) -> Callable:
        self._subs.append(fn)
        return lambda: self._subs.remove(fn)

    def emit(self, path: str) -> None:
        for fn in list(self._subs):
            try:
                fn(path)
            except Exception:
                pass


skillsChanged = _SkillsChangedSignal()
subscribe = skillsChanged.subscribe
skillChangeDetector: Any = None


async def _get_watchable_paths() -> List[str]:
    """Gather skill and command directories to watch."""
    paths: List[str] = []
    try:
        from vivian_cli.utils.skills import skills
        roots = await skills.get_skill_roots()
        for root in roots:
            if os.path.isdir(root):
                paths.append(root)
    except (ImportError, Exception):
        pass

    try:
        from vivian_cli.utils.commands import commands
        cmd_roots = await commands.get_command_dirs()
        for d in cmd_roots:
            if os.path.isdir(d):
                paths.append(d)
    except (ImportError, Exception):
        pass

    return list(set(paths))


def _handle_change(path: str) -> None:
    """Handle a filesystem change event with debounce."""
    global _debounce_timer, _pending_change_path
    _pending_change_path = path
    if _debounce_timer:
        _debounce_timer.cancel()
    _debounce_timer = threading.Timer(_DEBOUNCE_SECONDS, _fire_change)
    _debounce_timer.daemon = True
    _debounce_timer.start()


def _fire_change() -> None:
    """Emit skill change signal and clear caches."""
    global _pending_change_path
    path = _pending_change_path or ''
    logger.debug(f"SkillChangeDetector: change detected at {path}")
    try:
        from vivian_cli.utils.skills import skills
        skills.clear_cache()
    except ImportError:
        pass
    skillsChanged.emit(path)


async def initialize(overrides: Optional[Dict] = None) -> None:
    """Initialize file watching for skill directories."""
    global _watcher, _initialized
    if _initialized:
        return
    _initialized = True

    paths = await _get_watchable_paths()
    if not paths:
        return

    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler

        class _Handler(FileSystemEventHandler):
            def on_any_event(self, event: Any) -> None:
                if not event.is_directory:
                    _handle_change(getattr(event, 'src_path', ''))

        observer = Observer()
        handler = _Handler()
        for p in paths:
            observer.schedule(handler, p, recursive=True)
        observer.start()
        _watcher = observer
        logger.debug(f"SkillChangeDetector: watching {len(paths)} path(s)")
    except ImportError:
        logger.debug("watchdog not available; skill change detection disabled")
    except Exception as e:
        logger.debug(f"SkillChangeDetector init error: {e}")


def dispose() -> None:
    """Stop the file watcher."""
    global _watcher, _initialized, _debounce_timer
    if _debounce_timer:
        _debounce_timer.cancel()
        _debounce_timer = None
    if _watcher:
        try:
            _watcher.stop()
        except Exception:
            pass
        _watcher = None
    _initialized = False


async def reset_for_testing(overrides: Optional[Dict] = None) -> None:
    """Reset internal state for testing."""
    dispose()
    if overrides:
        pass  # apply overrides if needed
    await initialize(overrides)


resetForTesting = reset_for_testing

