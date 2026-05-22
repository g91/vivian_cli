"""Port of src/utils/hooks/hookEvents.ts"""
from __future__ import annotations
from typing import Any, Optional, Callable, Literal

ALWAYS_EMITTED_HOOK_EVENTS = ('SessionStart', 'Setup')
MAX_PENDING_EVENTS = 100

HookStartedEvent = dict  # type, hookId, hookName, hookEvent
HookProgressEvent = dict
HookResponseEvent = dict
HookExecutionEvent = dict
HookEventHandler = Callable[[HookExecutionEvent], None]

_pending_events: list[HookExecutionEvent] = []
_event_handler: Optional[HookEventHandler] = None
_all_hook_events_enabled = False

HOOK_EVENTS = [
    'PreToolUse', 'PostToolUse', 'PostToolUseFailure', 'PermissionDenied',
    'Notification', 'UserPromptSubmit', 'SessionStart', 'Stop', 'StopFailure',
    'SubagentStart', 'SubagentStop', 'PreCompact', 'PostCompact',
    'CwdChanged', 'FileChanged', 'Setup',
]


def register_hook_event_handler(handler: Optional[HookEventHandler]) -> None:
    global _event_handler
    _event_handler = handler
    if handler and _pending_events:
        for event in list(_pending_events):
            _pending_events.remove(event)
            handler(event)


def _emit(event: HookExecutionEvent) -> None:
    if _event_handler:
        _event_handler(event)
    else:
        _pending_events.append(event)
        if len(_pending_events) > MAX_PENDING_EVENTS:
            _pending_events.pop(0)


def _should_emit(hook_event: str) -> bool:
    if hook_event in ALWAYS_EMITTED_HOOK_EVENTS:
        return True
    return _all_hook_events_enabled and hook_event in HOOK_EVENTS


def emit_hook_started(hook_id: str, hook_name: str, hook_event: str) -> None:
    if not _should_emit(hook_event):
        return
    _emit({'type': 'started', 'hookId': hook_id, 'hookName': hook_name, 'hookEvent': hook_event})


def emit_hook_progress(data: dict) -> None:
    if not _should_emit(data.get('hookEvent', '')):
        return
    _emit({'type': 'progress', **data})


def start_hook_progress_interval(
    hook_id: str,
    hook_name: str,
    hook_event: str,
    get_output: Callable[[], dict],
    interval_ms: int = 1000,
) -> Callable[[], None]:
    """Start a background thread that periodically emits hook progress events."""
    import threading

    if not _should_emit(hook_event):
        return lambda: None

    stop_event = threading.Event()
    last_emitted = {'output': ''}

    def _run() -> None:
        while not stop_event.wait(interval_ms / 1000.0):
            try:
                out = get_output()
                if out.get('output') != last_emitted['output']:
                    last_emitted['output'] = out.get('output', '')
                    emit_hook_progress({
                        'hookId': hook_id,
                        'hookName': hook_name,
                        'hookEvent': hook_event,
                        'stdout': out.get('stdout', ''),
                        'stderr': out.get('stderr', ''),
                        'output': out.get('output', ''),
                    })
            except Exception:
                pass

    t = threading.Thread(target=_run, daemon=True)
    t.start()

    def stop() -> None:
        stop_event.set()

    return stop


def emit_hook_response(data: dict) -> None:
    output_to_log = data.get('stdout') or data.get('stderr') or data.get('output', '')
    if output_to_log:
        try:
            from vivian_cli.utils.debug import log_for_debugging
            log_for_debugging(
                f"Hook {data.get('hookName')} ({data.get('hookEvent')}) {data.get('outcome')}:\n{output_to_log}"
            )
        except ImportError:
            pass

    if not _should_emit(data.get('hookEvent', '')):
        return
    _emit({'type': 'response', **data})


def set_all_hook_events_enabled(enabled: bool) -> None:
    global _all_hook_events_enabled
    _all_hook_events_enabled = enabled


def clear_hook_event_state() -> None:
    global _event_handler, _all_hook_events_enabled
    _event_handler = None
    _pending_events.clear()
    _all_hook_events_enabled = False
