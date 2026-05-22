"""Port of src/utils/hooks/postSamplingHooks.ts"""
from __future__ import annotations
from typing import Any, Optional, Callable, Dict, List
import asyncio
import logging

logger = logging.getLogger(__name__)

# Type aliases
REPLHookContext = Dict[str, Any]
PostSamplingHook = Callable[[REPLHookContext], Any]

# Internal registry for post-sampling hooks
_post_sampling_hooks: List[PostSamplingHook] = []


def register_post_sampling_hook(hook: PostSamplingHook) -> None:
    """Register a post-sampling hook called after model sampling completes."""
    _post_sampling_hooks.append(hook)


# Alias for TS-style callers
registerPostSamplingHook = register_post_sampling_hook


def clear_post_sampling_hooks() -> None:
    """Clear all registered post-sampling hooks (for testing)."""
    _post_sampling_hooks.clear()


clearPostSamplingHooks = clear_post_sampling_hooks


async def execute_post_sampling_hooks(
    messages: List[Any],
    system_prompt: Any,
    user_context: Dict[str, str],
    system_context: Dict[str, str],
    tool_use_context: Any,
    query_source: Optional[str] = None,
) -> None:
    """Execute all registered post-sampling hooks."""
    context: REPLHookContext = {
        'messages': messages,
        'systemPrompt': system_prompt,
        'userContext': user_context,
        'systemContext': system_context,
        'toolUseContext': tool_use_context,
        'querySource': query_source,
    }
    for hook in _post_sampling_hooks:
        try:
            result = hook(context)
            if asyncio.iscoroutine(result):
                await result
        except Exception as e:
            logger.error(f"Post-sampling hook error: {e}")


executePostSamplingHooks = execute_post_sampling_hooks

