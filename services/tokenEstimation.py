"""Token estimation service — mirrors src/services/tokenEstimation.ts."""

from __future__ import annotations

from typing import Any, Optional


TOKEN_COUNT_THINKING_BUDGET = 1024
TOKEN_COUNT_MAX_TOKENS = 2048

DEFAULT_BYTES_PER_TOKEN = 4
JSON_BYTES_PER_TOKEN = 2


def roughTokenCountEstimation(content: str, bytesPerToken: float = DEFAULT_BYTES_PER_TOKEN) -> int:
    """Rough token count estimation based on character count.

    Mirrors roughTokenCountEstimation() from tokenEstimation.ts.
    """
    if not content:
        return 0
    return max(1, int((len(content.encode("utf-8")) + bytesPerToken - 1) // bytesPerToken))


def bytesPerTokenForFileType(fileExtension: str) -> float:
    """Return a better bytes/token estimate for known dense file formats."""
    ext = fileExtension.lower().lstrip(".")
    if ext in {"json", "jsonl", "map", "har"}:
        return JSON_BYTES_PER_TOKEN
    return DEFAULT_BYTES_PER_TOKEN


def roughTokenCountEstimationForFileType(content: str, fileExtension: str) -> int:
    return roughTokenCountEstimation(content, bytesPerTokenForFileType(fileExtension))


def _extract_text_from_content(content: Any) -> int:
    if isinstance(content, str):
        return roughTokenCountEstimation(content)
    if not isinstance(content, list):
        return 0

    total = 0
    for block in content:
        if isinstance(block, str):
            total += roughTokenCountEstimation(block)
            continue
        if not isinstance(block, dict):
            continue
        block_type = block.get("type")
        if block_type == "text":
            total += roughTokenCountEstimation(block.get("text", ""))
        elif block_type == "tool_use":
            import json

            total += roughTokenCountEstimation(json.dumps(block.get("input", {}), default=str))
        elif block_type == "tool_result":
            total += _extract_text_from_content(block.get("content", ""))
    return total


def roughTokenCountEstimationForMessage(message: dict) -> int:
    """Rough token count for a single message dict.

    Mirrors roughTokenCountEstimationForMessage() from tokenEstimation.ts.
    """
    content = message.get("content")
    if content is None and isinstance(message.get("message"), dict):
        content = message["message"].get("content")
    return _extract_text_from_content(content)


def roughTokenCountEstimationForMessages(messages: list[dict]) -> int:
    """Rough token count for a list of messages.

    Mirrors roughTokenCountEstimationForMessages() from tokenEstimation.ts.
    """
    return sum(roughTokenCountEstimationForMessage(m) for m in messages)


async def countTokensWithAPI(content: str) -> Optional[int]:
    """Count tokens using the Anthropic API.

    Mirrors countTokensWithAPI() from tokenEstimation.ts.
    Returns None on error.
    """
    try:
        from .api.client import getAnthropicClient
        from ..utils.model.model import getSmallFastModel

        client = getAnthropicClient()
        model = getSmallFastModel()

        response = await client.messages.count_tokens(
            model=model,
            messages=[{"role": "user", "content": content}],
            system=[],
            tools=[],
        )
        return getattr(response, "input_tokens", None)
    except Exception:
        return None


async def countMessagesTokensWithAPI(
    messages: list[dict],
    tools: Optional[list] = None,
) -> Optional[int]:
    """Count tokens for messages using the API.

    Mirrors countMessagesTokensWithAPI() from tokenEstimation.ts.
    """
    try:
        from .api.client import getAnthropicClient
        from ..utils.model.model import getSmallFastModel

        client = getAnthropicClient()
        response = await client.messages.count_tokens(
            model=getSmallFastModel(),
            messages=messages,
            system=[],
            tools=tools or [],
        )
        return getattr(response, "input_tokens", None)
    except Exception:
        return None


async def countTokensViaHaikuFallback(
    messages: list[dict],
    tools: Optional[list] = None,
) -> Optional[int]:
    """Fallback token counting path using the same API count endpoint.

    Python currently uses the same count path as the primary implementation,
    but keeps the TS export surface intact for callers.
    """
    return await countMessagesTokensWithAPI(messages, tools)


count_tokens_with_api = countTokensWithAPI
count_messages_tokens_with_api = countMessagesTokensWithAPI
count_tokens_via_haiku_fallback = countTokensViaHaikuFallback
rough_token_count_estimation = roughTokenCountEstimation
bytes_per_token_for_file_type = bytesPerTokenForFileType
rough_token_count_estimation_for_file_type = roughTokenCountEstimationForFileType
rough_token_count_estimation_for_message = roughTokenCountEstimationForMessage
rough_token_count_estimation_for_messages = roughTokenCountEstimationForMessages
