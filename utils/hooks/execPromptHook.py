"""Port of src/utils/hooks/execPromptHook.ts - Execute prompt-based hooks."""
from __future__ import annotations
from typing import Any, Optional, Dict, List
import uuid
import asyncio
import json
import logging

logger = logging.getLogger(__name__)


async def exec_prompt_hook(
    hook: Dict[str, Any],
    hook_name: str,
    hook_event: str,
    json_input: str,
    signal: Any,
    tool_use_context: Any,
    messages: Optional[List[Any]] = None,
    tool_use_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute a prompt-based hook using an LLM.
    
    Sends a processed prompt to the model and interprets the JSON response.
    Returns a HookResult dict.
    """
    effective_tool_use_id = tool_use_id or f"hook-{uuid.uuid4()}"
    hook_timeout_ms = hook.get('timeout', 30) * 1000 if hook.get('timeout') else 30000

    try:
        from vivian_cli.utils.hooks.hookHelpers import add_arguments_to_prompt
        processed_prompt = add_arguments_to_prompt(hook.get('prompt', ''), json_input)
        logger.debug(f"Hooks: Processing prompt hook with prompt: {processed_prompt}")

        user_message = {'type': 'user', 'message': {'role': 'user', 'content': processed_prompt}}
        messages_to_query = ([*messages, user_message] if messages else [user_message])

        system_text = (
            'You are evaluating a hook in vivian Code.\n\n'
            'Your response must be a JSON object matching one of the following schemas:\n'
            '1. If the condition is met, return: {"ok": true}\n'
            '2. If the condition is not met, return: {"ok": false, "reason": "Reason for why it is not met"}'
        )

        try:
            from vivian_cli.services.api.vivian import query_model_without_streaming
            model = hook.get('model', 'vivian-haiku-4-5')
            response = await asyncio.wait_for(
                query_model_without_streaming(
                    messages=messages_to_query,
                    system_prompt=[{'type': 'text', 'text': system_text}],
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
            logger.debug(f"Hooks: Prompt hook could not call model: {e}")
            return {'hook': hook, 'outcome': 'success'}

        full_response = content.strip()
        logger.debug(f"Hooks: Model response: {full_response}")

        try:
            parsed = json.loads(full_response)
        except (json.JSONDecodeError, ValueError):
            return {
                'hook': hook,
                'outcome': 'non_blocking_error',
            }

        if not parsed.get('ok'):
            reason = parsed.get('reason', 'Condition not met')
            return {
                'hook': hook,
                'outcome': 'blocking',
                'blockingError': {
                    'blockingError': f"Prompt hook condition was not met: {reason}",
                    'command': hook.get('prompt', ''),
                },
                'preventContinuation': True,
                'stopReason': reason,
            }

        return {'hook': hook, 'outcome': 'success'}

    except asyncio.TimeoutError:
        return {'hook': hook, 'outcome': 'cancelled'}
    except Exception as e:
        logger.debug(f"Hooks: Prompt hook error: {e}")
        return {'hook': hook, 'outcome': 'non_blocking_error'}


execPromptHook = exec_prompt_hook

