"""Port of src/utils/hooksConfigManager - metadata and grouping for hook UI."""
from __future__ import annotations
from typing import Any, Optional, Dict, List

MatcherMetadata = Dict[str, Any]
HookEventMetadata = Dict[str, Any]


def get_hook_event_metadata(tool_names: List[str]) -> Dict[str, HookEventMetadata]:
    """Return metadata for each hook event type, memoized by sorted tool names."""
    return {
        'PreToolUse': {
            'summary': 'Before tool execution',
            'description': 'Input is JSON of tool call arguments.\nExit 0: stdout/stderr not shown\nExit 2: show stderr to model and block\nOther: show stderr to user only',
            'matcherMetadata': {'fieldToMatch': 'tool_name', 'values': tool_names},
        },
        'PostToolUse': {
            'summary': 'After tool execution',
            'description': 'Input is JSON with fields "inputs" and "response".\nExit 0: stdout in transcript mode\nExit 2: show stderr to model immediately\nOther: show stderr to user only',
            'matcherMetadata': {'fieldToMatch': 'tool_name', 'values': tool_names},
        },
        'PostToolUseFailure': {
            'summary': 'After tool execution fails',
            'description': 'Input is JSON with tool_name, error, error_type, etc.',
            'matcherMetadata': {'fieldToMatch': 'tool_name', 'values': tool_names},
        },
        'PermissionDenied': {
            'summary': 'After auto mode classifier denies a tool call',
            'description': 'Input is JSON with tool_name, tool_input, reason.',
            'matcherMetadata': {'fieldToMatch': 'tool_name', 'values': tool_names},
        },
        'Notification': {
            'summary': 'When notifications are sent',
            'description': 'Input is JSON with notification message and type.',
            'matcherMetadata': {'fieldToMatch': 'notification_type', 'values': [
                'permission_prompt', 'idle_prompt', 'auth_success',
                'elicitation_dialog', 'elicitation_complete', 'elicitation_response',
            ]},
        },
        'UserPromptSubmit': {
            'summary': 'When the user submits a prompt',
            'description': 'Input is JSON with original user prompt text.',
        },
        'SessionStart': {
            'summary': 'When a new session is started',
            'description': 'Input is JSON with session start source.',
            'matcherMetadata': {'fieldToMatch': 'source', 'values': ['startup', 'resume', 'clear', 'compact']},
        },
        'Stop': {
            'summary': 'Right before vivian concludes its response',
            'description': 'Exit 0: not shown\nExit 2: show stderr to model\nOther: show stderr to user only',
        },
        'StopFailure': {
            'summary': 'When the turn ends due to an API error',
            'description': 'Fires instead of Stop on API errors.',
        },
        'SubagentStart': {
            'summary': 'When a subagent is started',
            'description': 'Input is JSON with agent_id and agent_type.',
            'matcherMetadata': {'fieldToMatch': 'agent_type', 'values': []},
        },
        'SubagentStop': {
            'summary': 'Right before a subagent concludes its response',
            'description': 'Input is JSON with agent_id, agent_type, agent_transcript_path.',
            'matcherMetadata': {'fieldToMatch': 'agent_type', 'values': []},
        },
        'PreCompact': {
            'summary': 'Before conversation compaction',
            'description': 'Exit 0: stdout appended as custom compact instructions\nExit 2: block compaction',
            'matcherMetadata': {'fieldToMatch': 'trigger', 'values': ['manual', 'auto']},
        },
        'PostCompact': {
            'summary': 'After conversation compaction',
            'description': 'Input is JSON with compaction details and summary.',
        },
        'CwdChanged': {
            'summary': 'When the working directory changes',
            'description': 'Input is JSON with old_cwd and new_cwd.',
        },
        'FileChanged': {
            'summary': 'When a watched file changes',
            'description': 'Input is JSON with file path and event type.',
        },
        'Setup': {
            'summary': 'During initial setup',
            'description': 'Runs during application setup.',
        },
    }


getHookEventMetadata = get_hook_event_metadata


def group_hooks_by_event_and_matcher(app_state: Any, tool_names: List[str]) -> Dict[str, Dict[str, List[Any]]]:
    """Group hooks by event and matcher for UI display."""
    try:
        from vivian_cli.utils.hooks.hooksSettings import get_all_hooks
        all_hooks = get_all_hooks(app_state)
    except ImportError:
        all_hooks = []

    result: Dict[str, Dict[str, List[Any]]] = {}
    for hook in all_hooks:
        event = hook.event
        matcher = hook.matcher or ''
        if event not in result:
            result[event] = {}
        if matcher not in result[event]:
            result[event][matcher] = []
        result[event][matcher].append(hook)
    return result


groupHooksByEventAndMatcher = group_hooks_by_event_and_matcher


def get_sorted_matchers_for_event(hooks_by_event_and_matcher: Dict, event: str) -> List[str]:
    """Get sorted matchers for a specific event."""
    matchers = list(hooks_by_event_and_matcher.get(event, {}).keys())
    try:
        from vivian_cli.utils.hooks.hooksSettings import sort_matchers_by_priority
        return sort_matchers_by_priority(matchers, hooks_by_event_and_matcher, event)
    except ImportError:
        return matchers


getSortedMatchersForEvent = get_sorted_matchers_for_event


def get_hooks_for_matcher(hooks_by_event_and_matcher: Dict, event: str, matcher: str) -> List[Any]:
    """Get hooks for a specific event/matcher combination."""
    return hooks_by_event_and_matcher.get(event, {}).get(matcher, [])


getHooksForMatcher = get_hooks_for_matcher


def get_matcher_metadata(event: str, tool_names: List[str]) -> Optional[MatcherMetadata]:
    """Get matcher metadata for an event."""
    metadata = get_hook_event_metadata(tool_names)
    event_data = metadata.get(event, {})
    return event_data.get('matcherMetadata')


getMatcherMetadata = get_matcher_metadata

