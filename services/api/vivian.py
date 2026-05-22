"""vivian API — mirrors src/services/api/vivian.ts."""
from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Optional


async def queryModelWithoutStreaming(
    messages: Any,
    system_prompt: Optional[list] = None,
    thinking_config: Optional[dict] = None,
    tools: Optional[list] = None,
    signal: Optional[asyncio.Event] = None,
    options: Optional[dict] = None,
    **kwargs: Any,
) -> dict:
    """Query the model without streaming.

    Mirrors queryModelWithoutStreaming() from vivian.ts.
    """
    if isinstance(messages, dict) and "messages" in messages:
        request = dict(messages)
        messages = request.get("messages", [])
        if system_prompt is None:
            system_prompt = request.get("system_prompt", request.get("systemPrompt", []))
        if thinking_config is None:
            thinking_config = request.get(
                "thinking_config",
                request.get("thinkingConfig", {}),
            )
        if tools is None:
            tools = request.get("tools", [])
        if signal is None:
            signal = request.get("signal", request.get("abortSignal"))
        if options is None:
            options = request.get("options")

    options = options or {}
    if system_prompt is None:
        system_prompt = kwargs.pop("systemPrompt", [])
    if thinking_config is None:
        thinking_config = kwargs.pop("thinkingConfig", {})
    if tools is None:
        tools = kwargs.pop("tools", [])
    if signal is None and "abortSignal" in kwargs:
        signal = kwargs.pop("abortSignal")
    try:
        from .client import getAnthropicClient
        model = options.get("model", "vivian-3-5-haiku-latest")
        client = getAnthropicClient()
        response = await client.messages.create(
            model=model,
            max_tokens=4096,
            messages=messages or [],
            system=system_prompt or [],
            tools=tools or [],
        )
        content = response.content
        text = ""
        for block in content:
            if hasattr(block, "text"):
                text += block.text
        return {
            "type": "assistant",
            "message": {"id": response.id, "content": content},
            "text": text,
            "isApiErrorMessage": False,
        }
    except Exception as e:
        return {
            "type": "assistant",
            "message": {"content": []},
            "text": str(e),
            "isApiErrorMessage": True,
        }


def getAPIMetadata() -> dict:
    """Get API metadata to include in requests.

    Mirrors getAPIMetadata() from vivian.ts.
    """
    try:
        from ...bootstrap.state import get_session_id
        return {"user_id": get_session_id()}
    except Exception:
        return {}


def getExtraBodyParams() -> dict:
    """Get extra body params for API requests."""
    return {}


query_model_without_streaming = queryModelWithoutStreaming
get_api_metadata = getAPIMetadata
get_extra_body_params = getExtraBodyParams
getAPIMetadata = getAPIMetadata
getExtraBodyParams = getExtraBodyParams
