"""Port of src/utils/hooks/AsyncHookRegistry.ts - Global registry for async hooks."""
from __future__ import annotations
from typing import Any, Optional, Dict, List, Callable
import asyncio
import time
import logging

from vivian_cli.utils.hooks.hookEvents import emit_hook_response, start_hook_progress_interval

logger = logging.getLogger(__name__)

# Global registry state: processId -> PendingAsyncHook
_pending_hooks: Dict[str, Dict[str, Any]] = {}


def register_pending_async_hook(
    process_id: str,
    hook_id: str,
    async_response: Dict[str, Any],
    hook_name: str,
    hook_event: str,
    command: str,
    shell_command: Any = None,
    tool_name: Optional[str] = None,
    plugin_id: Optional[str] = None,
) -> None:
    """Register an async hook in the global pending registry."""
    timeout = async_response.get('asyncTimeout', 15000)
    logger.debug(f"Hooks: Registering async hook {process_id} ({hook_name}) with timeout {timeout}ms")

    def get_output() -> Dict[str, str]:
        hook = _pending_hooks.get(process_id)
        if not hook or not hook.get('shellCommand'):
            return {'stdout': '', 'stderr': '', 'output': ''}
        sc = hook['shellCommand']
        stdout = getattr(sc, 'stdout', '') or ''
        stderr = getattr(sc, 'stderr', '') or ''
        return {'stdout': stdout, 'stderr': stderr, 'output': stdout + stderr}

    stop_progress = start_hook_progress_interval(
        hook_id=hook_id,
        hook_name=hook_name,
        hook_event=hook_event,
        get_output=get_output,
    )

    _pending_hooks[process_id] = {
        'processId': process_id,
        'hookId': hook_id,
        'hookName': hook_name,
        'hookEvent': hook_event,
        'toolName': tool_name,
        'pluginId': plugin_id,
        'command': command,
        'startTime': time.time() * 1000,
        'timeout': timeout,
        'responseAttachmentSent': False,
        'shellCommand': shell_command,
        'stopProgressInterval': stop_progress,
    }


registerPendingAsyncHook = register_pending_async_hook


def get_pending_async_hooks() -> List[Dict[str, Any]]:
    """Return all pending async hooks that have not yet been delivered."""
    return [h for h in _pending_hooks.values() if not h.get('responseAttachmentSent')]


getPendingAsyncHooks = get_pending_async_hooks


async def check_for_async_hook_responses() -> List[Dict[str, Any]]:
    """Check all registered async hooks and return completed ones."""
    responses: List[Dict[str, Any]] = []
    to_remove: List[str] = []

    for process_id, hook in list(_pending_hooks.items()):
        sc = hook.get('shellCommand')
        if sc is None:
            hook.get('stopProgressInterval', lambda: None)()
            to_remove.append(process_id)
            continue

        status = getattr(sc, 'status', 'running')
        if status == 'killed':
            hook.get('stopProgressInterval', lambda: None)()
            if hasattr(sc, 'cleanup'):
                sc.cleanup()
            to_remove.append(process_id)
            continue

        if status != 'completed':
            continue

        stdout = getattr(sc, 'stdout', '') or ''
        stderr = getattr(sc, 'stderr', '') or ''
        exit_code = getattr(sc, 'returncode', 0)

        if hook.get('responseAttachmentSent') or not stdout.strip():
            hook.get('stopProgressInterval', lambda: None)()
            to_remove.append(process_id)
            continue

        # Parse JSON response from stdout lines
        import json
        response: Dict[str, Any] = {}
        for line in stdout.split('\n'):
            stripped = line.strip()
            if stripped.startswith('{'):
                try:
                    parsed = json.loads(stripped)
                    if 'async' not in parsed:
                        response = parsed
                        break
                except json.JSONDecodeError:
                    pass

        hook['responseAttachmentSent'] = True
        hook.get('stopProgressInterval', lambda: None)()
        if hasattr(sc, 'cleanup'):
            sc.cleanup()

        responses.append({
            'processId': process_id,
            'response': response,
            'hookName': hook['hookName'],
            'hookEvent': hook['hookEvent'],
            'toolName': hook.get('toolName'),
            'pluginId': hook.get('pluginId'),
            'stdout': stdout,
            'stderr': stderr,
            'exitCode': exit_code,
        })

        emit_hook_response({
            'hookId': hook['hookId'],
            'hookName': hook['hookName'],
            'hookEvent': hook['hookEvent'],
            'output': stdout + stderr,
            'stdout': stdout,
            'stderr': stderr,
            'exitCode': exit_code,
            'outcome': 'success' if exit_code == 0 else 'error',
        })

    for pid in to_remove:
        _pending_hooks.pop(pid, None)

    return responses


checkForAsyncHookResponses = check_for_async_hook_responses


def remove_delivered_async_hooks(process_ids: List[str]) -> None:
    """Remove hooks that have been delivered from the registry."""
    for pid in process_ids:
        hook = _pending_hooks.get(pid)
        if hook and hook.get('responseAttachmentSent'):
            hook.get('stopProgressInterval', lambda: None)()
            _pending_hooks.pop(pid, None)


removeDeliveredAsyncHooks = remove_delivered_async_hooks


async def finalize_pending_async_hooks() -> None:
    """Finalize all still-pending async hooks (e.g. on shutdown)."""
    for process_id, hook in list(_pending_hooks.items()):
        sc = hook.get('shellCommand')
        hook.get('stopProgressInterval', lambda: None)()
        stdout = getattr(sc, 'stdout', '') or '' if sc else ''
        stderr = getattr(sc, 'stderr', '') or '' if sc else ''
        if sc and hasattr(sc, 'cleanup'):
            sc.cleanup()
        emit_hook_response({
            'hookId': hook.get('hookId', ''),
            'hookName': hook.get('hookName', ''),
            'hookEvent': hook.get('hookEvent', ''),
            'output': stdout + stderr,
            'stdout': stdout,
            'stderr': stderr,
            'outcome': 'cancelled',
        })
    _pending_hooks.clear()


finalizePendingAsyncHooks = finalize_pending_async_hooks


def clear_all_async_hooks() -> None:
    """Clear all async hooks from registry."""
    for hook in _pending_hooks.values():
        hook.get('stopProgressInterval', lambda: None)()
    _pending_hooks.clear()


clearAllAsyncHooks = clear_all_async_hooks

