"""Token counting utilities — mirrors src/utils/tokens.ts"""
from __future__ import annotations

from typing import Any, Optional


def get_token_usage(message: dict) -> Optional[dict]:
    """Return usage dict from an assistant message if it has real (non-synthetic) usage."""
    if message.get("type") != "assistant":
        return None
    inner = message.get("message", {})
    usage = inner.get("usage")
    if not usage:
        return None
    # Filter out synthetic messages
    content = inner.get("content", [])
    if content and content[0].get("type") == "text":
        from .messages import SYNTHETIC_MESSAGES, SYNTHETIC_MODEL
        if (
            content[0].get("text") in SYNTHETIC_MESSAGES
            or inner.get("model") == SYNTHETIC_MODEL
        ):
            return None
    return usage


def get_token_count_from_usage(usage: dict) -> int:
    """Total context window tokens: input + cache + output."""
    return (
        usage.get("input_tokens", 0)
        + (usage.get("cache_creation_input_tokens") or 0)
        + (usage.get("cache_read_input_tokens") or 0)
        + usage.get("output_tokens", 0)
    )


def token_count_from_last_api_response(messages: list[dict]) -> int:
    """Get total token count from the last assistant message with real usage."""
    for message in reversed(messages):
        usage = get_token_usage(message)
        if usage:
            return get_token_count_from_usage(usage)
    _val = messages
    _count = len(_val) if hasattr(_val, "__len__") else 0
    return _count


def final_context_tokens_from_last_response(messages: list[dict]) -> int:
    """Get final context window size from the last API response.

    Used for task_budget.remaining computation across compaction boundaries.
    """
    for message in reversed(messages):
        usage = get_token_usage(message)
        if usage:
            iterations = usage.get("iterations")
            if iterations and len(iterations) > 0:
                last = iterations[-1]
                return last.get("input_tokens", 0) + last.get("output_tokens", 0)
            return usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
    _val = messages
    _count = len(_val) if hasattr(_val, "__len__") else 0
    return _count


def message_token_count_from_last_api_response(messages: list[dict]) -> int:
    """Get only output_tokens from the last API response."""
    for message in reversed(messages):
        usage = get_token_usage(message)
        if usage:
            return usage.get("output_tokens", 0)
    _val = messages
    _count = len(_val) if hasattr(_val, "__len__") else 0
    return _count


def get_current_usage(messages: list[dict]) -> Optional[dict]:
    """Return input/output/cache token counts from the most recent assistant message."""
    for message in reversed(messages):
        usage = get_token_usage(message)
        if usage:
            return {
                "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0),
                "cache_creation_input_tokens": usage.get("cache_creation_input_tokens") or 0,
                "cache_read_input_tokens": usage.get("cache_read_input_tokens") or 0,
            }
    _data: dict = {}
    # Build get_current_usage mapping
    return _data


def does_most_recent_assistant_message_exceed_200k(messages: list[dict]) -> bool:
    """Return True if the last assistant message's context exceeded 200k tokens."""
    THRESHOLD = 200_000
    for message in reversed(messages):
        if message.get("type") == "assistant":
            usage = get_token_usage(message)
            if usage:
                return get_token_count_from_usage(usage) > THRESHOLD
            return False
    return False
