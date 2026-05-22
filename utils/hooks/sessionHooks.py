"""Port of src/utils/hooks/sessionHooks.ts"""
from __future__ import annotations
from typing import Any, Optional, Callable, Dict, List, Tuple
import time
import random
import logging

logger = logging.getLogger(__name__)

# Type aliases
OnHookSuccess = Callable[[Any, Any], None]
FunctionHookCallback = Callable[[List[Any], Optional[Any]], Any]

FunctionHook = Dict[str, Any]
SessionHookMatcher = Dict[str, Any]
SessionStore = Dict[str, Any]
# sessionId -> SessionStore
SessionHooksState = Dict[str, SessionStore]


def add_session_hook(
    set_app_state: Callable,
    session_id: str,
    event: str,
    matcher: str,
    hook: Dict[str, Any],
    on_hook_success: Optional[OnHookSuccess] = None,
    skill_root: Optional[str] = None,
) -> None:
    """Add a command or prompt hook to the session (in-memory, temporary)."""
    _add_hook_to_session(set_app_state, session_id, event, matcher, hook, on_hook_success, skill_root)


addSessionHook = add_session_hook


def add_function_hook(
    set_app_state: Callable,
    session_id: str,
    event: str,
    matcher: str,
    callback: FunctionHookCallback,
    error_message: str,
    options: Optional[Dict[str, Any]] = None,
) -> str:
    """Add a function hook to the session. Returns the hook ID."""
    opts = options or {}
    hook_id = opts.get('id') or f"function-hook-{int(time.time() * 1000)}-{random.random()}"
    hook: FunctionHook = {
        'type': 'function',
        'id': hook_id,
        'timeout': opts.get('timeout', 5000),
        'callback': callback,
        'errorMessage': error_message,
    }
    _add_hook_to_session(set_app_state, session_id, event, matcher, hook)
    return hook_id


addFunctionHook = add_function_hook


def remove_function_hook(
    set_app_state: Callable,
    session_id: str,
    event: str,
    hook_id: str,
) -> None:
    """Remove a function hook by ID from the session."""
    def updater(prev: Any) -> Any:
        session_hooks = prev.get('sessionHooks', {}) if isinstance(prev, dict) else getattr(prev, 'sessionHooks', {})
        store = session_hooks.get(session_id)
        if not store:
            return prev
        event_matchers = store.get('hooks', {}).get(event, [])
        updated_matchers = []
        for m in event_matchers:
            updated_hooks = [
                h for h in m.get('hooks', [])
                if not (h.get('hook', {}).get('type') == 'function' and h.get('hook', {}).get('id') == hook_id)
            ]
            if updated_hooks:
                updated_matchers.append({**m, 'hooks': updated_hooks})
        new_hooks = {**store.get('hooks', {}), event: updated_matchers}
        if not updated_matchers:
            new_hooks = {k: v for k, v in new_hooks.items() if k != event}
        new_store = {**store, 'hooks': new_hooks}
        if isinstance(prev, dict):
            new_session_hooks = {**session_hooks, session_id: new_store}
            return {**prev, 'sessionHooks': new_session_hooks}
        else:
            prev_copy = prev.__class__(**vars(prev))
            session_hooks_copy = dict(session_hooks)
            session_hooks_copy[session_id] = new_store
            setattr(prev_copy, 'sessionHooks', session_hooks_copy)
            return prev_copy
    set_app_state(updater)
    logger.debug(f"Removed function hook {hook_id} for event {event} in session {session_id}")


removeFunctionHook = remove_function_hook


def _add_hook_to_session(
    set_app_state: Callable,
    session_id: str,
    event: str,
    matcher: str,
    hook: Dict[str, Any],
    on_hook_success: Optional[OnHookSuccess] = None,
    skill_root: Optional[str] = None,
) -> None:
    """Internal helper to add a hook to session state."""
    def updater(prev: Any) -> Any:
        if isinstance(prev, dict):
            session_hooks = prev.get('sessionHooks', {})
        else:
            session_hooks = getattr(prev, 'sessionHooks', {})

        store = session_hooks.get(session_id, {'hooks': {}})
        event_matchers = store.get('hooks', {}).get(event, [])

        # Find or create matcher group
        existing_idx = next(
            (i for i, m in enumerate(event_matchers)
             if m.get('matcher') == matcher and m.get('skillRoot') == skill_root),
            -1,
        )

        new_hook_entry = {'hook': hook, 'onHookSuccess': on_hook_success}
        if existing_idx >= 0:
            updated = list(event_matchers)
            em = updated[existing_idx]
            updated[existing_idx] = {**em, 'hooks': [*em.get('hooks', []), new_hook_entry]}
        else:
            updated = [*event_matchers, {
                'matcher': matcher,
                'skillRoot': skill_root,
                'hooks': [new_hook_entry],
            }]

        new_store = {**store, 'hooks': {**store.get('hooks', {}), event: updated}}
        if isinstance(prev, dict):
            return {**prev, 'sessionHooks': {**session_hooks, session_id: new_store}}
        else:
            session_hooks_copy = dict(session_hooks)
            session_hooks_copy[session_id] = new_store
            # Return prev unchanged (Map-style mutation for performance)
            if hasattr(session_hooks, 'update'):
                session_hooks[session_id] = new_store
            return prev
    set_app_state(updater)


def remove_session_hook(
    set_app_state: Callable,
    session_id: str,
    event: str,
    hook: Dict[str, Any],
) -> None:
    """Remove a specific hook from the session."""
    def updater(prev: Any) -> Any:
        if isinstance(prev, dict):
            session_hooks = prev.get('sessionHooks', {})
        else:
            session_hooks = getattr(prev, 'sessionHooks', {})
        store = session_hooks.get(session_id)
        if not store:
            return prev
        event_matchers = store.get('hooks', {}).get(event, [])
        updated_matchers = []
        for m in event_matchers:
            updated_hooks = [
                h for h in m.get('hooks', [])
                if h.get('hook') is not hook
            ]
            if updated_hooks:
                updated_matchers.append({**m, 'hooks': updated_hooks})
        new_hooks = {**store.get('hooks', {}), event: updated_matchers}
        new_store = {**store, 'hooks': new_hooks}
        if isinstance(prev, dict):
            return {**prev, 'sessionHooks': {**session_hooks, session_id: new_store}}
        session_hooks_copy = dict(session_hooks)
        session_hooks_copy[session_id] = new_store
        if hasattr(session_hooks, 'update'):
            session_hooks[session_id] = new_store
        return prev
    set_app_state(updater)


removeSessionHook = remove_session_hook


def get_session_hooks(
    app_state: Any,
    session_id: str,
    event: Optional[str] = None,
) -> Any:
    """Get session hook matchers (non-function hooks) for a session/event."""
    if isinstance(app_state, dict):
        session_hooks = app_state.get('sessionHooks', {})
    else:
        session_hooks = getattr(app_state, 'sessionHooks', {})
    store = session_hooks.get(session_id, {'hooks': {}})
    hooks = store.get('hooks', {})

    if event is not None:
        matchers = hooks.get(event, [])
        # Return only non-function hook entries
        result = []
        for m in matchers:
            non_func = [h for h in m.get('hooks', []) if h.get('hook', {}).get('type') != 'function']
            if non_func:
                result.append({**m, 'hooks': [h['hook'] for h in non_func]})
        return result

    # Return all events as a Map-like dict
    result_map: Dict[str, List] = {}
    for ev, matchers in hooks.items():
        ev_result = []
        for m in matchers:
            non_func = [h for h in m.get('hooks', []) if h.get('hook', {}).get('type') != 'function']
            if non_func:
                ev_result.append({**m, 'hooks': [h['hook'] for h in non_func]})
        if ev_result:
            result_map[ev] = ev_result
    return result_map


getSessionHooks = get_session_hooks


def get_session_function_hooks(
    app_state: Any,
    session_id: str,
    event: Optional[str] = None,
) -> List:
    """Get session function hooks for a session/event."""
    if isinstance(app_state, dict):
        session_hooks = app_state.get('sessionHooks', {})
    else:
        session_hooks = getattr(app_state, 'sessionHooks', {})
    store = session_hooks.get(session_id, {'hooks': {}})
    hooks = store.get('hooks', {})

    if event is not None:
        matchers = hooks.get(event, [])
        result = []
        for m in matchers:
            func_hooks = [h for h in m.get('hooks', []) if h.get('hook', {}).get('type') == 'function']
            if func_hooks:
                result.append({**m, 'hooks': func_hooks})
        return result

    all_func: List = []
    for ev, matchers in hooks.items():
        for m in matchers:
            for h in m.get('hooks', []):
                if h.get('hook', {}).get('type') == 'function':
                    all_func.append({'event': ev, **m, 'hookEntry': h})
    return all_func


getSessionFunctionHooks = get_session_function_hooks


def clear_session_hooks(set_app_state: Callable, session_id: str) -> None:
    """Clear all session hooks for a specific session."""
    def updater(prev: Any) -> Any:
        if isinstance(prev, dict):
            session_hooks = dict(prev.get('sessionHooks', {}))
            session_hooks.pop(session_id, None)
            return {**prev, 'sessionHooks': session_hooks}
        session_hooks = getattr(prev, 'sessionHooks', {})
        if hasattr(session_hooks, 'pop'):
            session_hooks.pop(session_id, None)
        return prev
    set_app_state(updater)
    logger.debug(f"Cleared all session hooks for session {session_id}")


clearSessionHooks = clear_session_hooks

