"""Port of src/utils/hooks/hooksSettings.ts"""
from __future__ import annotations
from typing import Any, Optional, Dict, List

HookSource = str


class IndividualHookConfig:
    def __init__(self, event: str, config: Dict[str, Any], matcher: Optional[str] = None,
                 source: str = 'userSettings', plugin_name: Optional[str] = None):
        self.event = event
        self.config = config
        self.matcher = matcher
        self.source = source
        self.plugin_name = plugin_name


DEFAULT_HOOK_SHELL = 'bash'


def is_hook_equal(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    """Check if two hooks are equal by type and command/prompt content."""
    if a.get('type') != b.get('type'):
        return False
    same_if = (a.get('if', '') == b.get('if', ''))
    t = a.get('type')
    if t == 'command':
        return (b.get('type') == 'command'
                and a.get('command') == b.get('command')
                and (a.get('shell') or DEFAULT_HOOK_SHELL) == (b.get('shell') or DEFAULT_HOOK_SHELL)
                and same_if)
    if t == 'prompt':
        return b.get('type') == 'prompt' and a.get('prompt') == b.get('prompt') and same_if
    if t == 'agent':
        return b.get('type') == 'agent' and a.get('prompt') == b.get('prompt') and same_if
    if t == 'http':
        return b.get('type') == 'http' and a.get('url') == b.get('url') and same_if
    if t == 'function':
        return False  # Function hooks have no stable identity
    return False


isHookEqual = is_hook_equal


def get_hook_display_text(hook: Dict[str, Any]) -> str:
    """Get display text for a hook."""
    if hook.get('statusMessage'):
        return hook['statusMessage']
    t = hook.get('type')
    if t == 'command':
        return hook.get('command', '')
    if t in ('prompt', 'agent'):
        return hook.get('prompt', '')
    if t == 'http':
        return hook.get('url', '')
    return t or 'unknown'


getHookDisplayText = get_hook_display_text


def get_all_hooks(app_state: Any) -> List[IndividualHookConfig]:
    """Get all hooks from all sources combined."""
    hooks: List[IndividualHookConfig] = []

    try:
        from vivian_cli.utils.settings.settings import get_settings_for_source, get_settings_file_path_for_source
    except ImportError:
        get_settings_for_source = lambda s: None
        get_settings_file_path_for_source = lambda s: None

    policy = get_settings_for_source('policySettings') or {}
    restricted = policy.get('allowManagedHooksOnly') is True

    if not restricted:
        sources = ['userSettings', 'projectSettings', 'localSettings']
        seen_files: set = set()
        for source in sources:
            try:
                fp = get_settings_file_path_for_source(source)
                if fp:
                    import os
                    rp = os.path.realpath(fp)
                    if rp in seen_files:
                        continue
                    seen_files.add(rp)
            except Exception:
                pass
            src_settings = get_settings_for_source(source) or {}
            for event, matchers in src_settings.get('hooks', {}).items():
                for matcher in (matchers or []):
                    for hook_cmd in matcher.get('hooks', []):
                        hooks.append(IndividualHookConfig(
                            event=event,
                            config=hook_cmd,
                            matcher=matcher.get('matcher'),
                            source=source,
                        ))

    # Session hooks
    try:
        from vivian_cli.utils.hooks.sessionHooks import get_session_hooks
        from vivian_cli.utils.state.appState import get_session_id
        session_id = get_session_id()
        session_hook_map = get_session_hooks(app_state, session_id)
        for event, matchers in session_hook_map.items():
            for m in matchers:
                for hook_cmd in m.get('hooks', []):
                    hooks.append(IndividualHookConfig(
                        event=event,
                        config=hook_cmd if isinstance(hook_cmd, dict) else {'type': 'function'},
                        matcher=m.get('matcher'),
                        source='sessionHook',
                    ))
    except Exception:
        pass

    return hooks


getAllHooks = get_all_hooks


def get_hooks_for_event(app_state: Any, event: str) -> List[IndividualHookConfig]:
    """Get all hooks for a specific event."""
    return [h for h in get_all_hooks(app_state) if h.event == event]


getHooksForEvent = get_hooks_for_event


def hook_source_description_display_string(source: str) -> str:
    """Human-readable description for a hook source."""
    descriptions = {
        'userSettings': 'User settings (~/.vivian/settings.json)',
        'projectSettings': 'Project settings (.vivian/settings.json)',
        'localSettings': 'Local settings (.vivian/settings.local.json)',
        'pluginHook': 'Plugin hooks (~/.vivian/plugins/*/hooks/hooks.json)',
        'sessionHook': 'Session hooks (in-memory, temporary)',
        'builtinHook': 'Built-in hooks (registered internally by vivian Code)',
    }
    return descriptions.get(source, source)


hookSourceDescriptionDisplayString = hook_source_description_display_string


def hook_source_header_display_string(source: str) -> str:
    headers = {
        'userSettings': 'User Settings',
        'projectSettings': 'Project Settings',
        'localSettings': 'Local Settings',
        'pluginHook': 'Plugin Hooks',
        'sessionHook': 'Session Hooks',
        'builtinHook': 'Built-in Hooks',
    }
    return headers.get(source, source)


hookSourceHeaderDisplayString = hook_source_header_display_string


def sort_matchers_by_priority(matchers: List[Any], hooks_by_event_and_matcher: Any, selected_event: str) -> List[Any]:
    """Sort matchers by priority (wildcard matchers last)."""
    def priority_key(m: Any) -> int:
        matcher_str = m.get('matcher', '') if isinstance(m, dict) else str(m)
        return 0 if matcher_str else 1  # Specific matchers before wildcards
    return sorted(matchers, key=priority_key)


sortMatchersByPriority = sort_matchers_by_priority

