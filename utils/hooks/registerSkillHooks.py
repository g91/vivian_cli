"""Port of src/utils/hooks/registerSkillHooks.ts"""
from __future__ import annotations
from typing import Any, Optional, Dict, List, Callable
import logging

from vivian_cli.utils.hooks.hookEvents import HOOK_EVENTS
from vivian_cli.utils.hooks.sessionHooks import add_session_hook, remove_session_hook

logger = logging.getLogger(__name__)


def register_skill_hooks(
    set_app_state: Callable,
    session_id: str,
    hooks: Dict[str, Any],
    skill_name: str,
    skill_root: Optional[str] = None,
) -> None:
    """Register hooks from a skill's frontmatter as session-scoped hooks.
    
    If a hook has 'once: true', it is removed after first successful execution.
    """
    registered_count = 0

    for event_name in HOOK_EVENTS:
        matchers = hooks.get(event_name)
        if not matchers:
            continue

        for matcher in matchers:
            for hook in matcher.get('hooks', []):
                on_hook_success = None
                if hook.get('once'):
                    def make_remover(h: Dict[str, Any], ev: str = event_name) -> Callable:
                        def _remover(*args: Any) -> None:
                            logger.debug(f"Removing one-shot hook for event {ev} in skill '{skill_name}'")
                            remove_session_hook(set_app_state, session_id, ev, h)
                        return _remover
                    on_hook_success = make_remover(hook)

                add_session_hook(
                    set_app_state,
                    session_id,
                    event_name,
                    matcher.get('matcher') or '',
                    hook,
                    on_hook_success,
                    skill_root,
                )
                registered_count += 1

    if registered_count > 0:
        logger.debug(f"Registered {registered_count} hooks from skill '{skill_name}'")


registerSkillHooks = register_skill_hooks

