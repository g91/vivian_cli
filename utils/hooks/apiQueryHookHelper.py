"""Port of src/utils/hooks/apiQueryHookHelper.ts - API query hook helpers."""
from __future__ import annotations
from typing import Any, Optional, Callable, Dict, List
import asyncio
import logging

logger = logging.getLogger(__name__)

ApiQueryHookContext = Any
ApiQueryHookConfig = Dict[str, Any]
ApiQueryResult = Any


def create_api_query_hook(config: ApiQueryHookConfig) -> Dict[str, Any]:
    """Create a post-sampling hook from an API query config dict.
    
    Config keys:
      - prompt (str): the system prompt or instruction for the hook
      - model (str): model name to query
      - should_run (Callable): optional filter taking (messages) -> bool
      - on_result (Callable): async callback taking (result_text, messages)
      - description (str): human-readable hook name
    """
    should_run: Optional[Callable] = config.get('shouldRun') or config.get('should_run')
    on_result: Optional[Callable] = config.get('onResult') or config.get('on_result')
    prompt: str = config.get('prompt', '')
    model: str = config.get('model', 'vivian-haiku-4-5')
    description: str = config.get('description', 'api query hook')

    async def hook_fn(messages: List[Any]) -> None:
        # Apply filter
        if should_run is not None:
            try:
                ok = should_run(messages)
                if asyncio.iscoroutine(ok):
                    ok = await ok
                if not ok:
                    return
            except Exception as e:
                logger.debug(f"ApiQueryHook filter error: {e}")
                return

        # Build messages for the query
        from vivian_cli.utils.hooks.skillImprovement import _format_recent_messages
        recent = _format_recent_messages(messages)
        query_content = f"{prompt}\n\nRecent conversation:\n{recent}"

        try:
            from vivian_cli.services.api.vivian import query_model_without_streaming
            resp = await query_model_without_streaming(
                messages=[{'type': 'user', 'message': {'role': 'user', 'content': query_content}}],
                system_prompt=[{'type': 'text', 'text': 'You are an AI assistant. Be concise.'}],
                model=model,
                tools=[],
            )
            content = resp.get('content', '')
            if isinstance(content, list):
                content = ' '.join(b.get('text', '') for b in content if isinstance(b, dict))
            content = content.strip()

            if on_result is not None and content:
                result = on_result(content, messages)
                if asyncio.iscoroutine(result):
                    await result
        except (ImportError, Exception) as e:
            logger.debug(f"ApiQueryHook query failed: {e}")

    return {
        'fn': hook_fn,
        'description': description,
    }


createApiQueryHook = create_api_query_hook
