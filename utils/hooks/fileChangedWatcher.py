"""Port of src/utils/hooks/fileChangedWatcher.ts - Watch files for hook triggers."""
from __future__ import annotations
from typing import Any, Optional, Callable, List
import os
import asyncio
import logging

logger = logging.getLogger(__name__)

_watcher: Any = None
_current_cwd: str = ''
_dynamic_watch_paths: List[str] = []
_dynamic_watch_paths_sorted: List[str] = []
_initialized = False
_has_env_hooks = False
_notify_callback: Optional[Callable[[str, bool], None]] = None


def set_env_hook_notifier(cb: Optional[Callable[[str, bool], None]]) -> None:
    """Set a callback for hook notifications (text, isError)."""
    global _notify_callback
    _notify_callback = cb


setEnvHookNotifier = set_env_hook_notifier


def _resolve_watch_paths(config: Optional[Any] = None) -> List[str]:
    """Resolve all paths to watch based on config FileChanged matchers."""
    if config is None:
        try:
            from vivian_cli.utils.hooks.hooksConfigSnapshot import get_hooks_config_from_snapshot
            config = get_hooks_config_from_snapshot()
        except ImportError:
            config = {}

    matchers = (config or {}).get('FileChanged', [])
    static_paths: List[str] = []
    for m in matchers:
        matcher_str = m.get('matcher', '')
        if not matcher_str:
            continue
        for name in matcher_str.split('|'):
            name = name.strip()
            if not name:
                continue
            if os.path.isabs(name):
                static_paths.append(name)
            else:
                static_paths.append(os.path.join(_current_cwd, name))

    all_paths = list(set(static_paths + _dynamic_watch_paths))
    return all_paths


def _handle_file_event(path: str, event: str) -> None:
    """Handle a file change event by executing FileChanged hooks."""
    logger.debug(f"FileChanged: {event} {path}")
    try:
        import asyncio as _asyncio
        loop = _asyncio.get_event_loop()
        if loop.is_running():
            _asyncio.ensure_future(_run_file_changed_hooks(path, event))
        else:
            loop.run_until_complete(_run_file_changed_hooks(path, event))
    except Exception as e:
        logger.debug(f"FileChanged hook dispatch error: {e}")


async def _run_file_changed_hooks(path: str, event: str) -> None:
    try:
        from vivian_cli.utils.hooks import hooks
        results = await hooks.execute_file_changed_hooks(path, event)
        for r in results.get('results', []):
            if not r.get('succeeded') and r.get('output') and _notify_callback:
                _notify_callback(r['output'], True)
    except ImportError:
        pass
    except Exception as e:
        if _notify_callback:
            _notify_callback(str(e), True)


def _start_watching(paths: List[str]) -> None:
    """Start filesystem watcher on the given paths."""
    global _watcher
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler

        class _Handler(FileSystemEventHandler):
            def on_modified(self, event: Any) -> None:
                if not event.is_directory:
                    _handle_file_event(event.src_path, 'change')
            def on_created(self, event: Any) -> None:
                if not event.is_directory:
                    _handle_file_event(event.src_path, 'add')
            def on_deleted(self, event: Any) -> None:
                if not event.is_directory:
                    _handle_file_event(event.src_path, 'unlink')

        observer = Observer()
        handler = _Handler()
        watched_dirs = set(os.path.dirname(p) for p in paths)
        for d in watched_dirs:
            if os.path.isdir(d):
                observer.schedule(handler, d, recursive=False)
        observer.start()
        _watcher = observer
        logger.debug(f"FileChanged: watching {len(paths)} paths")
    except ImportError:
        logger.debug("watchdog not available; FileChanged hooks will not fire")


def initialize_file_changed_watcher(cwd: str) -> None:
    """Initialize file watching for CwdChanged and FileChanged hooks."""
    global _initialized, _current_cwd, _has_env_hooks
    if _initialized:
        return
    _initialized = True
    _current_cwd = cwd

    try:
        from vivian_cli.utils.hooks.hooksConfigSnapshot import get_hooks_config_from_snapshot
        config = get_hooks_config_from_snapshot() or {}
    except ImportError:
        config = {}

    _has_env_hooks = bool(config.get('CwdChanged') or config.get('FileChanged'))
    paths = _resolve_watch_paths(config)
    if paths:
        _start_watching(paths)


initializeFileChangedWatcher = initialize_file_changed_watcher


def update_watch_paths(paths: List[str]) -> None:
    """Update the dynamic watch paths and restart watching if changed."""
    global _dynamic_watch_paths, _dynamic_watch_paths_sorted
    if not _initialized:
        return
    sorted_paths = sorted(paths)
    if sorted_paths == _dynamic_watch_paths_sorted:
        return
    _dynamic_watch_paths = paths
    _dynamic_watch_paths_sorted = sorted_paths
    _restart_watching()


updateWatchPaths = update_watch_paths


def _restart_watching() -> None:
    global _watcher
    if _watcher:
        try:
            _watcher.stop()
        except Exception:
            pass
        _watcher = None
    paths = _resolve_watch_paths()
    if paths:
        _start_watching(paths)


async def on_cwd_changed_for_hooks(old_cwd: str, new_cwd: str) -> None:
    """Called when the working directory changes; runs CwdChanged hooks."""
    global _current_cwd
    if old_cwd == new_cwd:
        return

    try:
        from vivian_cli.utils.hooks.hooksConfigSnapshot import get_hooks_config_from_snapshot
        config = get_hooks_config_from_snapshot() or {}
    except ImportError:
        config = {}

    if not (config.get('CwdChanged') or config.get('FileChanged')):
        return

    _current_cwd = new_cwd

    try:
        from vivian_cli.utils.sessionEnvironment import clear_cwd_env_files
        await clear_cwd_env_files()
    except ImportError:
        pass

    try:
        from vivian_cli.utils import hooks as hooks_mod
        await hooks_mod.execute_cwd_changed_hooks(old_cwd, new_cwd)
    except (ImportError, Exception) as e:
        logger.debug(f"CwdChanged hook failed: {e}")


onCwdChangedForHooks = on_cwd_changed_for_hooks


def dispose() -> None:
    """Stop the file watcher and clean up."""
    global _watcher, _initialized, _has_env_hooks
    if _watcher:
        try:
            _watcher.stop()
        except Exception:
            pass
        _watcher = None
    _initialized = False
    _has_env_hooks = False
    _dynamic_watch_paths.clear()
    _dynamic_watch_paths_sorted.clear()


def reset_file_changed_watcher_for_testing() -> None:
    dispose()


resetFileChangedWatcherForTesting = reset_file_changed_watcher_for_testing

