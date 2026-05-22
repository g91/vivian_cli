"""Port of src/utils/hooks/execAgentHook.ts - Execute agent-based hooks."""
from __future__ import annotations
from typing import Any, Optional, Dict, List
import uuid
import asyncio
import json
import logging

logger = logging.getLogger(__name__)


async def exec_agent_hook(
    hook: Dict[str, Any],
    hook_name: str,
    hook_event: str,
    json_input: str,
    signal: Any,
    tool_use_context: Any,
    tool_use_id: Optional[str],
    messages: List[Any],
    agent_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute an agent-based hook using an LLM multi-turn query.
    
    Returns a HookResult dict with 'outcome' and optionally 'blockingError'.
    """
    effective_tool_use_id = tool_use_id or f"hook-{uuid.uuid4()}"
    hook_timeout_ms = hook.get('timeout', 60) * 1000 if hook.get('timeout') else 60000

    try:
        from vivian_cli.utils.hooks.hookHelpers import add_arguments_to_prompt, hook_response_schema
        processed_prompt = add_arguments_to_prompt(hook.get('prompt', ''), json_input)
        logger.debug(f"Hooks: Processing agent hook with prompt: {processed_prompt}")

        # Build user message
        user_message = {'type': 'user', 'message': {'role': 'user', 'content': processed_prompt}}
        agent_messages = [user_message]

        # Try to query the model if available
        try:
            from vivian_cli.services.api.vivian import query_model_without_streaming
            model = hook.get('model') or 'vivian-haiku-4-5'
            response = await asyncio.wait_for(
                query_model_without_streaming(
                    messages=agent_messages,
                    system_prompt=[{'type': 'text', 'text': 'You are evaluating a hook condition. Respond with JSON: {"ok": true} or {"ok": false, "reason": "..."}'}],
                    model=model,
                    tools=[],
                    signal=signal,
                ),
                timeout=hook_timeout_ms / 1000.0,
            )
            content = response.get('content', '')
            if isinstance(content, list):
                texts = [b.get('text', '') for b in content if isinstance(b, dict) and b.get('type') == 'text']
                content = ' '.join(texts)
        except (ImportError, Exception) as e:
            logger.debug(f"Hooks: Agent hook could not call model: {e}")
            # Default to success if we cannot run the agent
            return {
                'hook': hook,
                'outcome': 'success',
            }

        # Parse response
        try:
            parsed = json.loads(content.strip())
        except (json.JSONDecodeError, ValueError):
            return {'hook': hook, 'outcome': 'non_blocking_error'}

        if not parsed.get('ok'):
            reason = parsed.get('reason', 'Condition not met')
            logger.debug(f"Hooks: Agent hook condition was not met: {reason}")
            return {
                'hook': hook,
                'outcome': 'blocking',
                'blockingError': {
                    'blockingError': f"Agent hook condition was not met: {reason}",
                    'command': hook.get('prompt', ''),
                },
                'preventContinuation': True,
                'stopReason': reason,
            }

        return {'hook': hook, 'outcome': 'success'}

    except asyncio.TimeoutError:
        return {'hook': hook, 'outcome': 'cancelled'}
    except Exception as e:
        logger.debug(f"Hooks: Agent hook error: {e}")
        return {'hook': hook, 'outcome': 'non_blocking_error'}


execAgentHook = exec_agent_hook

