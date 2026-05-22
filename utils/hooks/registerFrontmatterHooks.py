"""Port of src/utils/hooks/registerFrontmatterHooks.ts"""
from __future__ import annotations
from typing import Any, Optional, Dict, List, Callable
import logging

from vivian_cli.utils.hooks.hookEvents import HOOK_EVENTS
from vivian_cli.utils.hooks.sessionHooks import add_session_hook

logger = logging.getLogger(__name__)


def register_frontmatter_hooks(
    set_app_state: Callable,
    session_id: str,
    hooks: Dict[str, Any],
    source_name: str,
    is_agent: bool = False,
) -> None:
    """Register hooks from frontmatter (agent or skill) as session-scoped hooks.
    
    For agents, converts Stop hooks to SubagentStop since subagents trigger SubagentStop.
    """
    if not hooks or not hooks.keys():
        return

    hook_count = 0

    for event in HOOK_EVENTS:
        matchers = hooks.get(event)
        if not matchers:
            continue

        # Agents: convert Stop -> SubagentStop
        target_event = event
        if is_agent and event == 'Stop':
            target_event = 'SubagentStop'
            logger.debug(f"Converting Stop hook to SubagentStop for {source_name}")

        for matcher_config in matchers:
            matcher = matcher_config.get('matcher') or ''
            hooks_array = matcher_config.get('hooks', [])
            if not hooks_array:
                continue
            for hook in hooks_array:
                add_session_hook(set_app_state, session_id, target_event, matcher, hook)
                hook_count += 1

    if hook_count > 0:
        logger.debug(f"Registered {hook_count} frontmatter hook(s) from {source_name} for session {session_id}")


registerFrontmatterHooks = register_frontmatter_hooks

